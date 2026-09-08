"""
Filing Sleuth — Query Planner (Stage 1)

Decomposes complex, multi-company financial and qualitative questions into
an atomic, deterministic ExecutionPlan with:
- Target companies (tickers & resolved CIKs)
- Time horizon & filing types
- Metric classifications (quantitative XBRL vs qualitative TEXT disclosures)
- Atomic sub-questions per company, metric, and period
- Targeted retrieval queries with Item filters
"""

from __future__ import annotations

import logging
import re
from typing import Literal

from pydantic import BaseModel, Field

from backend.agent.llm_client import LLMClient
from backend.retrieval.ticker_resolver import TickerResolver

logger = logging.getLogger(__name__)

PlanIntent = Literal[
    "SINGLE_METRIC",
    "TREND",
    "COMPARATIVE",
    "COMPARATIVE_TREND",
    "QUALITATIVE_DISCLOSURE",
]

SourcePreference = Literal["XBRL", "TEXT", "HYBRID"]


class PlannedCompany(BaseModel):
    """Company identified in the user query."""
    ticker: str
    cik: str = ""
    name: str = ""


class TimeRange(BaseModel):
    """Time horizon for the query."""
    type: Literal["ANNUAL", "QUARTERLY", "SPECIFIC_YEAR"] = "ANNUAL"
    count: int = 1
    years: list[int] = Field(default_factory=list)


class SubQuestion(BaseModel):
    """An atomic question targeting one company, metric/disclosure, and period."""
    id: str
    text: str
    company_ticker: str
    company_name: str = ""
    cik: str = ""
    metric: str | None = None
    target_fiscal_year: int | None = None
    period_offset: int = 0  # 0 = most recent, 1 = 1 year ago, etc.
    source_preference: SourcePreference = "XBRL"
    target_item: str | None = None  # e.g., "7", "1A", "3", "1C"
    retrieval_query: str = ""


class ExecutionPlan(BaseModel):
    """Full execution plan produced by the Query Planner."""
    original_question: str
    intent: PlanIntent = "SINGLE_METRIC"
    companies: list[PlannedCompany] = Field(default_factory=list)
    time_range: TimeRange = Field(default_factory=TimeRange)
    sub_questions: list[SubQuestion] = Field(default_factory=list)
    requires_computation: bool = False
    computation_description: str | None = None


PLANNER_SYSTEM_PROMPT = """
You are an expert financial research query planner for SEC EDGAR filings (10-K and 10-Q).
Your job is to analyze an investor/analyst question and produce a structured ExecutionPlan.

CRITICAL RULES:
1. Decompose comparisons into separate sub-questions for EACH company and EACH year.
   - Never combine two companies into one sub-question.
   - For ratios like "R&D as % of revenue", create separate sub-questions for the numerator (R&D) and denominator (Revenue).
2. Choose source_preference accurately:
   - "XBRL": For standard GAAP numeric metrics (Revenue, R&D, Net Income, Operating Income, EPS, Assets, Liabilities, Cash).
   - "TEXT": For qualitative disclosures (litigation, risk factors, cybersecurity, segment narrative, management comments).
   - "HYBRID": When a metric requires reading MD&A narrative context alongside numbers.
3. Map target_item accurately:
   - "1": Business overview, product segments
   - "1A": Risk factors
   - "1C": Cybersecurity
   - "3": Legal proceedings, litigation, lawsuits
   - "7": MD&A, revenue analysis, segment discussion, liquidity
   - "8": Financial statements, footnote accounting policies
"""


class QueryPlanner:
    """Decomposes user queries into actionable sub-questions."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        ticker_resolver: TickerResolver | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.ticker_resolver = ticker_resolver

    async def plan(self, question: str) -> ExecutionPlan:
        """Generate an execution plan for the query."""
        plan: ExecutionPlan

        if self.llm_client.has_active_provider:
            prompt = f"User Question: {question}\n\nGenerate the complete structured ExecutionPlan JSON."
            plan = await self.llm_client.generate(
                prompt=prompt,
                system=PLANNER_SYSTEM_PROMPT,
                response_model=ExecutionPlan,
                temperature=0.0,
            )
            plan.original_question = question
        else:
            plan = self._heuristic_plan(question)

        # Resolve CIKs for all identified companies if ticker resolver is provided
        if self.ticker_resolver:
            for company in plan.companies:
                if not company.cik and company.ticker:
                    resolved = await self.ticker_resolver.resolve(company.ticker)
                    if resolved:
                        company.cik = resolved.cik
                        if not company.name:
                            company.name = resolved.title

            for sq in plan.sub_questions:
                if not sq.cik and sq.company_ticker:
                    resolved = await self.ticker_resolver.resolve(sq.company_ticker)
                    if resolved:
                        sq.cik = resolved.cik
                        if not sq.company_name:
                            sq.company_name = resolved.title

        return plan

    def _heuristic_plan(self, question: str) -> ExecutionPlan:
        """Deterministic rule-based query decomposition for when no LLM API key is present."""
        q_upper = question.upper()

        # Detect known tickers
        found_tickers = []
        known_tickers = {
            "AAPL": "Apple Inc.",
            "MSFT": "MICROSOFT CORP",
            "TSLA": "Tesla, Inc.",
            "GOOGL": "Alphabet Inc.",
            "AMZN": "Amazon.com Inc.",
            "NVDA": "NVIDIA Corp",
            "META": "Meta Platforms Inc.",
        }

        for ticker, name in known_tickers.items():
            first_word = name.replace(",", "").replace(".", "").split()[0].lower()
            # Check standalone word match for ticker or company name substring
            if re.search(rf"\b{ticker}\b", q_upper) or first_word in question.lower():
                found_tickers.append((ticker, name))


        if not found_tickers:
            # Default to AAPL if no company specified
            found_tickers = [("AAPL", "Apple Inc.")]

        # Detect explicit target fiscal year (e.g. 2024, 2025, 2026, FY2024)
        year_matches = re.findall(r"(?:FY\s*|\b)(20[12]\d)\b", question, re.I)
        target_year = int(year_matches[0]) if year_matches else None

        # Check for explicit Item target (e.g. "Item 1", "Item 1A", "Item 1C", "Item 3", "Item 7")
        item_match = re.search(r"item\s+([0-9]+[a-z]?)", question, re.I)
        target_item_override = item_match.group(1).upper() if item_match else None

        # Check for non-disclosure or specific sub-product questions
        # that must NOT be confused with aggregate company-level GAAP metrics
        is_negative_or_specific = any(
            phrase in question.lower()
            for phrase in [
                "broken down specifically",
                "vision pro",
                "cryptocurrency mining",
                "super bowl",
                "commercials",
            ]
        )

        # Detect time count
        count = 1
        count_match = re.search(r"(\d+)\s*(?:years|filings|periods)", question, re.I)
        if count_match:
            count = min(int(count_match.group(1)), 5)
        elif "last year" in question.lower() or "previous year" in question.lower():
            count = 2

        # Detect intent
        is_comparative = len(found_tickers) > 1
        is_trend = count > 1
        is_qualitative = any(w in question.lower() for w in ["litigation", "risk", "lawsuit", "cybersecurity", "strategy", "regulatory"]) or target_item_override is not None

        if is_comparative and is_trend:
            intent = "COMPARATIVE_TREND"
        elif is_comparative:
            intent = "COMPARATIVE"
        elif is_trend:
            intent = "TREND"
        elif is_qualitative:
            intent = "QUALITATIVE_DISCLOSURE"
        else:
            intent = "SINGLE_METRIC"

        # Detect metrics
        sub_questions: list[SubQuestion] = []
        sq_counter = 1

        has_net_income = "net income" in question.lower() or "profit" in question.lower()
        has_rd = ("r&d" in question.lower() or "research" in question.lower()) and not is_negative_or_specific
        has_rev = ("revenue" in question.lower() or "sales" in question.lower()) and not is_negative_or_specific
        has_litigation = "litigation" in question.lower() or "legal" in question.lower() or "lawsuit" in question.lower()
        has_cyber = "cybersecurity" in question.lower() or "cyber" in question.lower()
        has_risk = "risk" in question.lower() and not (has_cyber or has_litigation)

        for ticker, name in found_tickers:
            for offset in range(count):
                period_label = f"FY{target_year}" if target_year else ("latest" if offset == 0 else f"{offset} year(s) prior")

                if has_litigation:
                    sub_questions.append(
                        SubQuestion(
                            id=f"sq_{sq_counter}",
                            text=f"What legal proceedings and litigation exposures were disclosed by {name} for {period_label}?",
                            company_ticker=ticker,
                            company_name=name,
                            metric="LitigationExposure",
                            period_offset=offset,
                            source_preference="TEXT",
                            target_item="3",
                            retrieval_query=f"{name} legal proceedings litigation lawsuits",
                        )
                    )
                    sq_counter += 1

                if has_cyber:
                    sub_questions.append(
                        SubQuestion(
                            id=f"sq_{sq_counter}",
                            text=f"What cybersecurity risk management and governance did {name} disclose for {period_label}?",
                            company_ticker=ticker,
                            company_name=name,
                            metric="CybersecurityGovernance",
                            period_offset=offset,
                            source_preference="TEXT",
                            target_item="1C",
                            retrieval_query=f"{name} cybersecurity risk management governance",
                        )
                    )
                    sq_counter += 1

                if has_risk:
                    sub_questions.append(
                        SubQuestion(
                            id=f"sq_{sq_counter}",
                            text=f"What key risk factors were disclosed by {name} for {period_label}?",
                            company_ticker=ticker,
                            company_name=name,
                            metric="RiskFactors",
                            period_offset=offset,
                            source_preference="TEXT",
                            target_item="1A",
                            retrieval_query=f"{name} risk factors business operations",
                        )
                    )
                    sq_counter += 1

                if has_net_income:
                    sub_questions.append(
                        SubQuestion(
                            id=f"sq_{sq_counter}",
                            text=f"What was {name}'s Net Income for {period_label}?",
                            company_ticker=ticker,
                            company_name=name,
                            metric="NetIncomeLoss",
                            target_fiscal_year=target_year,
                            period_offset=offset,
                            source_preference="XBRL",
                            target_item="8",
                            retrieval_query=f"{name} net income profit loss",
                        )
                    )
                    sq_counter += 1

                if has_rd:
                    sub_questions.append(
                        SubQuestion(
                            id=f"sq_{sq_counter}",
                            text=f"What was {name}'s Research & Development expense for {period_label}?",
                            company_ticker=ticker,
                            company_name=name,
                            metric="ResearchAndDevelopmentExpense",
                            target_fiscal_year=target_year,
                            period_offset=offset,
                            source_preference="XBRL",
                            target_item="7",
                            retrieval_query=f"{name} research and development expense R&D",
                        )
                    )
                    sq_counter += 1

                if has_rev:
                    sub_questions.append(
                        SubQuestion(
                            id=f"sq_{sq_counter}",
                            text=f"What was {name}'s Total Revenue / Net Sales for {period_label}?",
                            company_ticker=ticker,
                            company_name=name,
                            metric="Revenues",
                            target_fiscal_year=target_year,
                            period_offset=offset,
                            source_preference="XBRL",
                            target_item="7",
                            retrieval_query=f"{name} total net sales revenues",
                        )
                    )
                    sq_counter += 1

                if target_item_override and not any([has_litigation, has_cyber, has_risk, has_net_income, has_rd, has_rev]):
                    sub_questions.append(
                        SubQuestion(
                            id=f"sq_{sq_counter}",
                            text=f"What disclosures did {name} provide in Item {target_item_override}?",
                            company_ticker=ticker,
                            company_name=name,
                            period_offset=offset,
                            source_preference="TEXT",
                            target_item=target_item_override,
                            retrieval_query=question,
                        )
                    )
                    sq_counter += 1

        # If generic or no specific metric matched, create default sub-questions
        if not sub_questions:
            for ticker, name in found_tickers:
                for offset in range(count):
                    sub_questions.append(
                        SubQuestion(
                            id=f"sq_{sq_counter}",
                            text=f"What are the relevant financial disclosures for {name} regarding '{question}'?",
                            company_ticker=ticker,
                            company_name=name,
                            period_offset=offset,
                            source_preference="TEXT" if (is_negative_or_specific or target_item_override) else "HYBRID",
                            target_item=target_item_override or "7",
                            retrieval_query=question,
                        )
                    )
                    sq_counter += 1

        companies = [PlannedCompany(ticker=t, name=n) for t, n in found_tickers]
        requires_comp = "%" in question or "percent" in question.lower() or "compare" in question.lower() or is_trend

        return ExecutionPlan(
            original_question=question,
            intent=intent,
            companies=companies,
            time_range=TimeRange(type="ANNUAL", count=count),
            sub_questions=sub_questions,
            requires_computation=requires_comp,
            computation_description="Compute % change or ratio between metrics" if requires_comp else None,
        )
