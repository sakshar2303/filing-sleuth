"""
Filing Sleuth — Pydantic Models for Filing Metadata

These models represent the structured data flowing between pipeline stages.
They're defined separately from the retrieval layer so they can be imported
by any stage without circular dependencies.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class CitationStatus(str, Enum):
    """Status of a fact extraction attempt."""
    FOUND = "FOUND"
    NOT_DISCLOSED = "NOT_DISCLOSED"
    AMBIGUOUS = "AMBIGUOUS"
    ERROR = "ERROR"


class ConfidenceLevel(str, Enum):
    """Confidence in an extracted fact."""
    HIGH = "HIGH"       # XBRL ground truth or verified quote
    MEDIUM = "MEDIUM"   # Text extraction with verified quote
    LOW = "LOW"         # Text extraction with unverified or fuzzy quote
    NONE = "NONE"       # No extraction possible


class SourceType(str, Enum):
    """How a fact was extracted."""
    XBRL = "XBRL"       # From XBRL CompanyFacts API (structured, ground truth)
    TEXT = "TEXT"        # From filing text via LLM extraction


class CompanyRef(BaseModel):
    """Reference to a company, resolved from user query."""
    name: str
    ticker: str
    cik: str  # 10-digit zero-padded


class MetricRef(BaseModel):
    """Reference to a financial metric."""
    name: str                           # Human-readable name (e.g., "Revenue")
    xbrl_tag: str | None = None         # XBRL concept if known
    type: str = "quantitative"          # "quantitative" or "qualitative"


class SubQuestion(BaseModel):
    """An atomic sub-question decomposed from the user's query."""
    id: str                             # e.g., "sq_1"
    text: str                           # The sub-question in natural language
    company_cik: str                    # Target company CIK
    metric: str | None = None           # Metric name or XBRL tag
    period: str | None = None           # e.g., "latest_fy", "latest_fy-1", "FY2023"
    requires_text_extraction: bool = False  # True if qualitative (no XBRL)


class QueryPlan(BaseModel):
    """Structured output from the Query Planner (Stage 1)."""
    original_query: str
    interpretation: str                 # How the planner interpreted ambiguous terms
    companies: list[CompanyRef]
    metrics: list[MetricRef]
    time_range: dict                    # Flexible: {"type": "relative", "periods": 2, ...}
    comparison_type: str                # "single", "multi_period", "cross_company", etc.
    sub_questions: list[SubQuestion]


class ExtractedFact(BaseModel):
    """Output from the Extraction Agent (Stage 6)."""
    sub_question_id: str
    status: CitationStatus
    claim: str | None = None            # Natural language claim
    value: float | int | None = None    # Numeric value (if quantitative)
    unit: str | None = None             # "USD", "shares", "pure", etc.
    period_start: str | None = None     # ISO date
    period_end: str | None = None       # ISO date
    fiscal_label: str | None = None     # e.g., "FY2023", "Q3 2024"
    company: str | None = None          # Company name
    cik: str | None = None
    accession_number: str | None = None
    source_type: SourceType | None = None
    xbrl_tag: str | None = None
    item_section: str | None = None     # e.g., "Item 1A: Risk Factors"
    exact_quote: str | None = None      # Direct quote from the filing
    quote_verified: bool | None = None  # True if quote fuzzy-matched against source
    confidence: ConfidenceLevel = ConfidenceLevel.NONE
    reason: str | None = None           # Explanation for NOT_DISCLOSED or AMBIGUOUS


class CrossRefResult(BaseModel):
    """Output from the Cross-Reference Engine (Stage 7)."""
    metric: str
    companies: list[str]
    periods: list[str]
    facts: list[ExtractedFact]
    deltas: list[dict] | None = None      # Year-over-year changes
    trend: str | None = None              # "increasing", "decreasing", "flat", "volatile"
    notes: list[str] = Field(default_factory=list)  # Warnings, caveats


class SynthesizedAnswer(BaseModel):
    """Final output from the Synthesis Agent (Stage 8)."""
    query: str
    answer_text: str                    # The narrative answer
    citations: list[ExtractedFact]      # All facts supporting the answer
    cross_references: list[CrossRefResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)  # Ambiguities, caveats
    uncited_claims_removed: int = 0     # Count of sentences stripped for lacking citations
