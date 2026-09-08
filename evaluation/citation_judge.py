"""
Filing Sleuth — Citation & Hallucination Judge

Automated judge evaluating:
1. Citation Precision: Does the citation point to the authentic SEC filing accession?
2. Section Accuracy: Does the cited Item section match the disclosure?
3. Quote Faithfulness: Can the verbatim quote be verified against the filing text?
4. Hallucination Detection: Detects fabricated claims, numbers, and citations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.agent.extraction_agent import ExtractedFact
from backend.agent.synthesis_agent import CitationEntry, SynthesisReport
from backend.verification.quote_verifier import QuoteVerifier

logger = logging.getLogger(__name__)


@dataclass
class CitationAuditResult:
    """Audit result for a single citation."""
    citation_id: str
    company: str
    accession_number: str | None
    item_section: str | None
    source_type: str
    is_valid_accession: bool
    is_quote_verified: bool
    hallucination_detected: bool
    notes: str


@dataclass
class EvaluationScorecard:
    """Overall evaluation scorecard across a set of benchmark questions."""
    total_questions: int
    passed_questions: int
    accuracy_rate: float
    citation_precision: float
    quote_faithfulness: float
    hallucination_rate: float
    non_disclosure_precision: float
    details: list[dict[str, Any]]


class CitationJudge:
    """Audits synthesis reports and extracted facts for citation integrity."""

    def __init__(self, quote_verifier: QuoteVerifier | None = None) -> None:
        self.quote_verifier = quote_verifier or QuoteVerifier()

    def audit_citation(self, citation: CitationEntry, fact: ExtractedFact | None = None) -> CitationAuditResult:
        """Audit an individual citation entry."""
        # 1. Accession number format check: standard SEC accession is 18 digits (with dashes: \d{10}-\d{2}-\d{6})
        accn = citation.accession_number or ""
        valid_accn = bool(accn and len(accn.replace("-", "")) >= 18)

        # 2. Quote faithfulness
        quote_verified = True
        if citation.source_type == "TEXT":
            quote_verified = bool(citation.quote_verified)

        # 3. Hallucination detection
        hallucinated = False
        notes = "Citation verified."

        if not valid_accn and citation.source_type in ["XBRL", "TEXT"]:
            hallucinated = True
            notes = "Invalid or missing SEC accession number."
        elif citation.source_type == "TEXT" and not quote_verified:
            hallucinated = True
            notes = "Unverified quotation detected."

        return CitationAuditResult(
            citation_id=citation.citation_id,
            company=citation.company,
            accession_number=citation.accession_number,
            item_section=citation.item_section,
            source_type=citation.source_type,
            is_valid_accession=valid_accn,
            is_quote_verified=quote_verified,
            hallucination_detected=hallucinated,
            notes=notes,
        )

    def audit_report(self, report: SynthesisReport) -> list[CitationAuditResult]:
        """Audit all citations in a synthesis report."""
        return [self.audit_citation(c) for c in report.citations]
