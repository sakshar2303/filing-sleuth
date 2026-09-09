"""
Filing Sleuth — Synthesis Agent (Stage 8)

Composes the final, investor-grade research report from extracted facts,
alignment matrices, and computed financial derivations.
Every claim is backed by an explicit citation footnote linking to accession
number, item section, and verified quote.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from backend.agent.extraction_agent import ExtractedFact
from backend.agent.llm_client import LLMClient
from backend.agent.query_planner import ExecutionPlan
from backend.crossref.alignment import AlignmentMatrix, CrossReferenceAligner
from backend.crossref.computations import ComputedResult, FinancialComputations

logger = logging.getLogger(__name__)


class CitationEntry(BaseModel):
    """A citation reference anchoring a claim to source EDGAR filing."""
    citation_id: str             # e.g., "[1]"
    company: str
    cik: str
    accession_number: str | None
    item_section: str | None
    source_type: str             # "XBRL" or "TEXT"
    xbrl_tag: str | None = None
    exact_quote: str | None = None
    quote_verified: bool | None = None


class SynthesisReport(BaseModel):
    """The final synthesized research report."""
    question: str
    executive_summary: str
    comparison_table_markdown: str = ""
    key_findings: list[str] = Field(default_factory=list)
    citations: list[CitationEntry] = Field(default_factory=list)
    caveats_and_notes: list[str] = Field(default_factory=list)


SYNTHESIS_SYSTEM_PROMPT = """
You are an elite financial research analyst preparing an investment memo based on SEC EDGAR filings.
Synthesize the provided extracted facts, aligned tables, and mathematical derivations into an authoritative SynthesisReport.

CRITICAL INTEGRITY INSTRUCTIONS:
1. Every claim, number, and quote must cite a corresponding source using inline footnotes like [1], [2].
2. Do NOT extrapolate or introduce external knowledge not present in the extracted facts.
3. If a metric was NOT_DISCLOSED, explicitly state the lack of disclosure.
4. Highlight any fiscal year calendar mismatches or tag variations in caveats_and_notes.
"""


class SynthesisAgent:
    """Produces the final investor report with grounded citations."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()
        self.aligner = CrossReferenceAligner()
        self.computer = FinancialComputations()

    async def synthesize(
        self,
        question: str,
        plan: ExecutionPlan,
        facts: list[ExtractedFact],
        skeptic_mode: bool = False,
    ) -> SynthesisReport:
        """Synthesize a complete research report from facts and plan."""
        # 1. Align facts and compute metrics
        matrix = self.aligner.align(facts)
        computations = self.computer.compute_all(facts, matrix)

        # 2. Build citations list from extracted facts (only for confirmed FOUND facts)
        citations: list[CitationEntry] = []
        for f in facts:
            if f.status != "FOUND":
                continue
            cid = f"[{len(citations)+1}]"
            citations.append(
                CitationEntry(
                    citation_id=cid,
                    company=f.company,
                    cik=f.cik,
                    accession_number=f.accession_number,
                    item_section=f.item_section,
                    source_type=f.source_type,
                    xbrl_tag=f.xbrl_tag,
                    exact_quote=f.exact_quote,
                    quote_verified=f.quote_verified,
                )
            )

        # 3. Generate structured report
        if self.llm_client.has_active_provider:
            return await self._synthesize_llm(question, plan, facts, matrix, computations, citations, skeptic_mode)

        return self._synthesize_heuristic(question, plan, facts, matrix, computations, citations, skeptic_mode)

    async def _synthesize_llm(
        self,
        question: str,
        plan: ExecutionPlan,
        facts: list[ExtractedFact],
        matrix: AlignmentMatrix,
        computations: list[ComputedResult],
        citations: list[CitationEntry],
        skeptic_mode: bool = False,
    ) -> SynthesisReport:
        """Generate synthesis report using LLM."""
        facts_summary = "\n".join(
            f"{c.citation_id} [{f.company} - FY{f.fiscal_year or 'N/A'}] {f.claim or 'Not Disclosed'} "
            f"(Source: {f.source_type} | Accn: {f.accession_number or 'N/A'})"
            for c, f in zip(citations, facts)
        )

        comp_summary = "\n".join(
            f"- {c.description} (Formula: {c.formula})"
            for c in computations
        )

        skeptic_instructions = ""
        system_prompt = SYNTHESIS_SYSTEM_PROMPT
        if skeptic_mode:
            system_prompt += (
                "\n\nFORENSIC SKEPTIC MODE IS ACTIVE:\n"
                "You are acting as an investigative forensic auditor / short-seller. "
                "Highlight aggressive revenue recognition, divergence between net income and operating cash flow, "
                "unusual footnote adjustments, customer/supplier concentrations, and liquidity risks. "
                "Explicitly point out any vulnerabilities in executive_summary and key_findings."
            )
            skeptic_instructions = "\n[MODE: FORENSIC SKEPTIC - Focus on accounting red flags, cash-flow quality gaps, and footnote risks]\n"

        prompt = (
            f"User Question: {question}\n\n"
            f"{skeptic_instructions}"
            f"Extracted Facts:\n{facts_summary}\n\n"
            f"Calculated Derivations:\n{comp_summary}\n\n"
            f"Calendar Notes: {', '.join(matrix.calendar_warnings) if matrix.calendar_warnings else 'None'}\n\n"
            f"Generate the full SynthesisReport JSON."
        )

        report = await self.llm_client.generate(
            prompt=prompt,
            system=system_prompt,
            response_model=SynthesisReport,
            temperature=0.0,
        )
        report.question = question
        report.citations = citations
        return report

    def _synthesize_heuristic(
        self,
        question: str,
        plan: ExecutionPlan,
        facts: list[ExtractedFact],
        matrix: AlignmentMatrix,
        computations: list[ComputedResult],
        citations: list[CitationEntry],
        skeptic_mode: bool = False,
    ) -> SynthesisReport:
        """Deterministic heuristic report builder for when no LLM API key is present."""
        # 1. Executive Summary
        prefix = "[FORENSIC SKEPTIC AUDIT] " if skeptic_mode else ""
        if computations:
            comp_descs = " ".join(c.description for c in computations[:3])
            exec_summary = f"{prefix}Analysis for '{question}': {comp_descs}"
        elif facts:
            valid_claims = [f.claim for f in facts if f.claim]
            exec_summary = f"{prefix}Analysis for '{question}': " + " ".join(valid_claims[:3])
        else:
            exec_summary = f"{prefix}No disclosures found for '{question}' in the target filings."

        if skeptic_mode:
            exec_summary += " [Skeptic Lens: Operating cash flow, working capital trajectory, and footnote commitments should be reconciled against GAAP accruals.]"

        # 2. Markdown comparison table
        table_lines = []
        if matrix.companies and matrix.fiscal_years:
            header = "| Metric | Company | " + " | ".join(f"FY{y}" for y in matrix.fiscal_years) + " |"
            sep = "| --- | --- | " + " | ".join("---:" for _ in matrix.fiscal_years) + " |"
            table_lines.extend([header, sep])

            for row in matrix.rows:
                for comp in matrix.companies:
                    vals = []
                    for y in matrix.fiscal_years:
                        cell = row.cells.get((comp, y))
                        vals.append(cell.formatted_value if cell else "—")
                    table_lines.append(f"| {row.metric_name} | {comp} | " + " | ".join(vals) + " |")

        table_md = "\n".join(table_lines)

        # 3. Key findings with citation markers
        findings: list[str] = []
        for i, (f, c) in enumerate(zip(facts, citations)):
            if f.claim:
                findings.append(f"{f.claim} {c.citation_id}")

        for comp in computations:
            findings.append(f"{comp.description} (Calculated via {comp.formula})")

        # 4. Caveats & Notes
        caveats = list(matrix.calendar_warnings)
        unverified_quotes = [f for f in facts if f.source_type == "TEXT" and f.quote_verified is False]
        if unverified_quotes:
            caveats.append(f"Warning: {len(unverified_quotes)} text claim(s) could not be verified against source text.")

        return SynthesisReport(
            question=question,
            executive_summary=exec_summary,
            comparison_table_markdown=table_md,
            key_findings=findings,
            citations=citations,
            caveats_and_notes=caveats,
        )
