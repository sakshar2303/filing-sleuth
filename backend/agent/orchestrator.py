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
    trace: list[PipelineTraceStep] = field(default_factory=list)
    total_chunks_indexed: int = 0
    all_quotes_verified: bool = True


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

        self._indexed_filings: set[str] = set()

    async def run(
        self,
        question: str,
        on_trace_step: Any = None,
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

        logger.info("Executing pipeline for query: '%s'", question)
        await record_step("START", f"Received research query: '{question}'")

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

        # Step 4: Computations (e.g. ratios, trend deltas) if needed
        computations: list[dict[str, Any]] = []
        if plan.requires_computation:
            computations = self._run_computations(extracted_facts)
            if computations:
                await record_step(
                    "COMPUTATION",
                    f"Computed {len(computations)} cross-metric ratios / deltas",
                    {"computations": computations},
                )

        # Step 5: Synthesize final report with grounded citations
        synthesis_report = await self.synthesis_agent.synthesize(question, plan, extracted_facts)
        await record_step(
            "SYNTHESIS",
            f"Synthesized report with {len(synthesis_report.citations)} citations",
            {"summary": synthesis_report.executive_summary},
        )

        await record_step("COMPLETE", "Pipeline execution finished successfully")

        return PipelineResult(
            question=question,
            plan=plan,
            extracted_facts=extracted_facts,
            synthesis_report=synthesis_report,
            computations=computations,
            trace=trace,
            total_chunks_indexed=total_indexed,
            all_quotes_verified=all_quotes_verified,
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
