"""
Filing Sleuth — Agent Orchestrator

The main pipeline controller. Glues all layers together:
1. Stage 1: Query Planner (decompose question into ExecutionPlan)
2. Stage 2-4: Retrieval, Parsing, Indexing (ensure data is fetched and indexed)
3. Stage 6: Extraction Agent (extract facts via XBRL or Text)
4. Stage 7: Quote Verification (verify exact text quotes against sources)
5. Returns a verified execution trace ready for UI and evaluation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.agent.extraction_agent import ExtractedFact, ExtractionAgent
from backend.agent.llm_client import LLMClient

from backend.agent.query_planner import ExecutionPlan, QueryPlanner, SubQuestion
from backend.agent.synthesis_agent import SynthesisAgent, SynthesisReport
from backend.crossref.financial_dossier import CompanyFinancialDossier, FinancialDossierEngine
from backend.crossref.forensic_radar import ForensicRadarEngine, ForensicScorecard
from backend.indexing.bm25_index import BM25Index
from backend.indexing.hybrid_search import HybridSearchEngine
from backend.indexing.vector_store import VectorStore
from backend.parsing.chunk_builder import ChunkBuilder, FilingMetadata
from backend.parsing.section_parser import SectionParser
from backend.retrieval.filing_fetcher import FilingFetcher
from backend.retrieval.sec_client import SECClient
from backend.retrieval.submissions import SubmissionsAPI
from backend.retrieval.ticker_resolver import TickerResolver
from backend.retrieval.xbrl_facts import XBRLFactsAPI
from backend.verification.quote_verifier import QuoteVerifier

logger = logging.getLogger(__name__)


@dataclass
class PipelineTraceStep:
    """A recorded reasoning/execution step in the pipeline trace."""
    step_name: str
    description: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """The complete result of running the research pipeline on a question."""
    question: str
    plan: ExecutionPlan
    extracted_facts: list[ExtractedFact]
    synthesis_report: SynthesisReport | None = None
    computations: list[dict[str, Any]] = field(default_factory=list)
    forensic_scorecard: dict[str, Any] | None = None
    financial_dossier: dict[str, Any] | None = None
    chart_data: dict[str, Any] | None = None
    trace: list[PipelineTraceStep] = field(default_factory=list)
    total_chunks_indexed: int = 0
    all_quotes_verified: bool = True
    skeptic_mode: bool = False


class Orchestrator:
    """Coordinates end-to-end SEC filing research and grounded extraction.

    Usage:
        async with SECClient() as sec_client:
            orchestrator = Orchestrator(sec_client)
            result = await orchestrator.run("What was Apple's R&D spend for the last 2 years?")
    """

    def __init__(
        self,
        sec_client: SECClient,
        vector_store: VectorStore | None = None,
        bm25_index: BM25Index | None = None,
        llm_client: LLMClient | None = None,
        quote_verifier: QuoteVerifier | None = None,
    ) -> None:
        self.sec_client = sec_client
        self.ticker_resolver = TickerResolver(sec_client)
        self.submissions_api = SubmissionsAPI(sec_client)
        self.xbrl_api = XBRLFactsAPI(sec_client)
        self.filing_fetcher = FilingFetcher(sec_client)

        self.section_parser = SectionParser()
        self.chunk_builder = ChunkBuilder()
        self.vector_store = vector_store or VectorStore()
        self.bm25_index = bm25_index or BM25Index()
        self.search_engine = HybridSearchEngine(self.vector_store, self.bm25_index)

        self.llm_client = llm_client or LLMClient()
        self.quote_verifier = quote_verifier or QuoteVerifier()

        self.query_planner = QueryPlanner(
            llm_client=self.llm_client,
            ticker_resolver=self.ticker_resolver,
        )
        self.extraction_agent = ExtractionAgent(
            xbrl_api=self.xbrl_api,
            search_engine=self.search_engine,
            llm_client=self.llm_client,
            quote_verifier=self.quote_verifier,
        )
        self.synthesis_agent = SynthesisAgent(llm_client=self.llm_client)
        self.forensic_engine = ForensicRadarEngine()
        self.dossier_engine = FinancialDossierEngine()

        self._indexed_filings: set[str] = set()

    async def run(
        self,
        question: str,
        on_trace_step: Any = None,
        skeptic_mode: bool = False,
    ) -> PipelineResult:
        """Run the research pipeline end-to-end on a user question."""
        trace: list[PipelineTraceStep] = []

        async def record_step(name: str, desc: str, data: dict[str, Any] | None = None) -> None:
            step = PipelineTraceStep(name, desc, data or {})
            trace.append(step)
            if on_trace_step:
                try:
                    import inspect
                    if inspect.iscoroutinefunction(on_trace_step):
                        await on_trace_step(step)
                    else:
                        on_trace_step(step)
                except Exception as ex:
                    logger.warning("Error in on_trace_step callback: %s", ex)

        logger.info("Executing pipeline for query: '%s' (skeptic_mode=%s)", question, skeptic_mode)
        await record_step("START", f"Received research query: '{question}'")

        if skeptic_mode:
            await record_step(
                "SKEPTIC_MODE",
                "Forensic Skeptic Mode active — auditing for accounting red flags, cash-flow divergence, and footnote risks",
                {"skeptic_mode": True},
            )

        # Step 1: Plan query execution
        plan = await self.query_planner.plan(question)
        await record_step(
            "PLANNING",
            f"Generated execution plan with {len(plan.sub_questions)} sub-questions (intent: {plan.intent})",
            {"plan": plan.model_dump()},
        )

        # Step 2: Ensure required filings are fetched and indexed
        total_indexed = 0
        needs_text_indexing = any(sq.source_preference in ["TEXT", "HYBRID"] for sq in plan.sub_questions)

        for company in plan.companies:
            if not company.cik and company.ticker:
                resolved = await self.ticker_resolver.resolve(company.ticker)
                if resolved:
                    company.cik = resolved.cik
                    company.name = resolved.title

            if not company.cik:
                logger.warning("Could not resolve CIK for ticker %s", company.ticker)
                continue

            # Check if text indexing is required
            if needs_text_indexing:
                filing_res = await self.submissions_api.get_filings(
                    company.cik,
                    form_types=["10-K"],
                    limit=plan.time_range.count,
                )

                for filing in filing_res.filings:
                    filing_key = f"{company.cik}_{filing.accession_number}"
                    if filing_key in self._indexed_filings:
                        continue

                    try:
                        html = await self.filing_fetcher.fetch_filing(
                            cik=company.cik,
                            accession_number=filing.accession_number,
                            primary_document=filing.primary_document,
                        )
                        parsed = self.section_parser.parse(html)
                        meta = FilingMetadata(
                            company=company.name,
                            cik=company.cik,
                            accession_number=filing.accession_number,
                            form_type=filing.form_type,
                            filing_date=filing.filing_date,
                            reporting_date=filing.reporting_date,
                        )
                        chunks = self.chunk_builder.build_chunks(parsed.sections, meta)
                        counts = self.search_engine.index_filing_chunks(chunks)
                        self._indexed_filings.add(filing_key)
                        total_indexed += counts["vector"]
                        await record_step(
                            "INDEXING",
                            f"Indexed {len(chunks)} chunks for {company.name} ({filing.accession_number})",
                            {"cik": company.cik, "chunks": len(chunks)},
                        )
                    except Exception as e:
                        logger.error("Failed to fetch/index filing %s: %s", filing.accession_number, e)

        # Step 3: Execute extraction for each sub-question
        extracted_facts: list[ExtractedFact] = []
        all_quotes_verified = True

        for sq in plan.sub_questions:
            # Ensure sub-question has resolved CIK
            if not sq.cik and sq.company_ticker:
                matching_comp = next((c for c in plan.companies if c.ticker == sq.company_ticker), None)
                if matching_comp:
                    sq.cik = matching_comp.cik
                    sq.company_name = matching_comp.name

            fact = await self.extraction_agent.extract(sq)
            extracted_facts.append(fact)

            if fact.source_type == "TEXT" and fact.quote_verified is False:
                all_quotes_verified = False

            await record_step(
                "EXTRACTION",
                f"Extracted fact for [{sq.company_ticker}] {sq.id}: {fact.status} via {fact.source_type}",
                {"fact": fact.model_dump()},
            )

        # Step 4: Multi-Year Financial Dossier & Deep Computations
        computations: list[dict[str, Any]] = []
        primary_dossier: CompanyFinancialDossier | None = None
        chart_data: dict[str, Any] | None = None
        financial_dossier: dict[str, Any] | None = None
        forensic_scorecard: dict[str, Any] | None = None

        target_comps = list({f.company for f in extracted_facts if f.company})
        if not target_comps and plan.companies:
            target_comps = [c.ticker for c in plan.companies if c.ticker]

        if target_comps:
            primary_comp = target_comps[0]
            comp_obj = next((c for c in plan.companies if c.ticker == primary_comp or c.name == primary_comp), None)
            cik = comp_obj.cik if comp_obj else None
            comp_name = comp_obj.name if comp_obj else primary_comp

            if not cik:
                try:
                    resolved = await self.ticker_resolver.resolve(primary_comp)
                    if resolved:
                        cik = resolved.cik
                        comp_name = resolved.title
                except Exception:
                    pass

            if cik:
                try:
                    raw_facts = await self.xbrl_api.get_company_facts_raw(cik)
                    dossier, extra_facts, extra_comps = self.dossier_engine.extract_dossier(
                        primary_comp, comp_name, cik, raw_facts
                    )
                    if dossier and dossier.series:
                        primary_dossier = dossier
                        chart_data = dossier.chart_payload
                        financial_dossier = dossier.model_dump()

                        # Augment extracted_facts with verified multi-year statement facts (avoiding duplicates)
                        existing_ids = {f.sub_question_id for f in extracted_facts}
                        for ef in extra_facts:
                            if ef.sub_question_id not in existing_ids:
                                extracted_facts.append(ef)

                        # Augment computations with multi-year margins and YoY growth rates
                        for ec in extra_comps:
                            computations.append(ec.__dict__)

                        await record_step(
                            "FINANCIAL_DOSSIER",
                            f"Generated Multi-Year Financial Statement Dossier for {comp_name} ({len(dossier.series)} fiscal periods: {dossier.fiscal_years})",
                            {"kpis": dossier.summary_kpis},
                        )

                        # Step 4b: Compute Forensic Radar from the same raw_facts
                        target_year = None
                        if plan.time_range and plan.time_range.years:
                            target_year = plan.time_range.years[0]
                        elif plan.sub_questions:
                            target_year = next((sq.target_fiscal_year for sq in plan.sub_questions if sq.target_fiscal_year), None)
                        scorecard = self.forensic_engine.evaluate_from_raw_facts(primary_comp, raw_facts, fiscal_year=target_year)
                        if scorecard:
                            forensic_scorecard = scorecard.to_dict()
                            await record_step(
                                "FORENSIC_RADAR",
                                f"Computed Forensic Health Scorecard for {primary_comp}: {scorecard.overall_score}/100 ({scorecard.status_label})",
                                {"scorecard": forensic_scorecard},
                            )
                except Exception as ex:
                    logger.warning("Failed to extract financial dossier for %s: %s", primary_comp, ex)

        # If plan required explicit computations (e.g. peer ratios), run them
        if plan.requires_computation:
            extra_planned_comps = self._run_computations(extracted_facts)
            if extra_planned_comps:
                computations.extend(extra_planned_comps)
                await record_step(
                    "COMPUTATION",
                    f"Computed {len(extra_planned_comps)} cross-metric ratios / deltas",
                    {"computations": extra_planned_comps},
                )

        # Fallback forensic scorecard if not computed from raw_facts
        if not forensic_scorecard and target_comps:
            scorecard = self.forensic_engine.evaluate_company(target_comps[0], extracted_facts)
            if scorecard:
                forensic_scorecard = scorecard.to_dict()

        # Step 5: Synthesize final report with grounded citations and multi-year dossier
        synthesis_report = await self.synthesis_agent.synthesize(
            question, plan, extracted_facts, skeptic_mode=skeptic_mode, dossier=primary_dossier
        )
        await record_step(
            "SYNTHESIS",
            f"Synthesized report with {len(synthesis_report.citations)} citations",
            {"summary": synthesis_report.executive_summary[:200] + "..."},
        )

        await record_step("COMPLETE", "Pipeline execution finished successfully")

        return PipelineResult(
            question=question,
            plan=plan,
            extracted_facts=extracted_facts,
            synthesis_report=synthesis_report,
            computations=computations,
            forensic_scorecard=forensic_scorecard,
            financial_dossier=financial_dossier,
            chart_data=chart_data,
            trace=trace,
            total_chunks_indexed=total_indexed,
            all_quotes_verified=all_quotes_verified,
            skeptic_mode=skeptic_mode,
        )

    def _run_computations(self, facts: list[ExtractedFact]) -> list[dict[str, Any]]:
        """Compute ratios (e.g. R&D as % of Revenue) and growth deltas."""
        computations: list[dict[str, Any]] = []

        # Group facts by (company, fiscal_year)
        by_company_year: dict[tuple[str, int | None], dict[str, ExtractedFact]] = {}
        for f in facts:
            if f.value is not None and f.xbrl_tag:
                key = (f.company, f.fiscal_year)
                by_company_year.setdefault(key, {})[f.xbrl_tag] = f

        # Check for R&D as % of Revenue
        for (company, year), metric_map in by_company_year.items():
            rd_fact = next((f for tag, f in metric_map.items() if "ResearchAndDevelopment" in tag), None)
            rev_fact = next((f for tag, f in metric_map.items() if "Revenue" in tag or "Sales" in tag), None)

            if rd_fact and rev_fact and rev_fact.value and rev_fact.value != 0:
                ratio = (rd_fact.value / rev_fact.value) * 100.0
                computations.append({
                    "type": "RATIO_PERCENT",
                    "company": company,
                    "fiscal_year": year,
                    "numerator_label": "R&D Expense",
                    "numerator_value": rd_fact.value,
                    "denominator_label": "Revenue / Net Sales",
                    "denominator_value": rev_fact.value,
                    "result_value": round(ratio, 2),
                    "result_formatted": f"{ratio:.2f}%",
                    "description": f"{company}'s R&D spend was {ratio:.2f}% of revenue in FY{year}.",
                })

        return computations
