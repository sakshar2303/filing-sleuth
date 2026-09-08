"""
Filing Sleuth — Cross-Reference Alignment Engine (Stage 7)

Aligns extracted facts across multiple companies and fiscal periods into a
coherent comparison matrix. Flags fiscal calendar mismatches (e.g. Apple ends
in September, Microsoft ends in June, Tesla ends in December).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.agent.extraction_agent import ExtractedFact

logger = logging.getLogger(__name__)


@dataclass
class MetricCell:
    """A single cell in the alignment matrix."""
    company: str
    fiscal_year: int
    value: float | int | None
    formatted_value: str
    unit: str | None
    fact: ExtractedFact | None


@dataclass
class AlignedMetricRow:
    """A row in the alignment matrix representing a specific metric across companies/years."""
    metric_name: str
    cells: dict[tuple[str, int], MetricCell] = field(default_factory=dict)


@dataclass
class AlignmentMatrix:
    """Structured comparison grid across companies and periods."""
    companies: list[str]
    fiscal_years: list[int]
    rows: list[AlignedMetricRow] = field(default_factory=list)
    calendar_warnings: list[str] = field(default_factory=list)

    def get_cell(self, metric: str, company: str, year: int) -> MetricCell | None:
        """Convenience: retrieve a specific cell."""
        for r in self.rows:
            if r.metric_name.lower() == metric.lower():
                return r.cells.get((company, year))
        return None


def _format_cell_value(val: float | int | None, unit: str | None) -> str:
    """Format numbers into readable financial representations ($34.55B, $120M)."""
    if val is None:
        return "N/D"

    abs_val = abs(val)
    prefix = "$" if unit == "USD" else ""
    sign = "-" if val < 0 else ""

    if abs_val >= 1_000_000_000:
        return f"{sign}{prefix}{abs_val / 1_000_000_000:.2f}B"
    elif abs_val >= 1_000_000:
        return f"{sign}{prefix}{abs_val / 1_000_000:.2f}M"
    elif abs_val >= 1_000:
        return f"{sign}{prefix}{abs_val / 1_000:.2f}K"
    else:
        return f"{sign}{prefix}{abs_val:,.2f}" if isinstance(val, float) else f"{sign}{prefix}{abs_val:,}"


def _clean_metric_title(raw: str | None) -> str:
    """Convert raw XBRL tags or metric names to clean display titles."""
    if not raw:
        return "Metric"
    name = raw.split(":")[-1]
    if name in ["ResearchAndDevelopmentExpense", "research_and_development"]:
        return "Research & Development"
    if name in ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "revenue"]:
        return "Total Revenue / Net Sales"
    if name in ["NetIncomeLoss", "net_income"]:
        return "Net Income"
    if name in ["OperatingIncomeLoss", "operating_income"]:
        return "Operating Income"
    if name in ["GrossProfit", "gross_profit"]:
        return "Gross Profit"
    # Fallback: split CamelCase
    import re
    return re.sub(r"(?<!^)(?=[A-Z])", " ", name)


class CrossReferenceAligner:
    """Aligns facts into a comparison matrix and detects reporting discrepancies."""

    def align(self, facts: list[ExtractedFact]) -> AlignmentMatrix:
        """Build an AlignmentMatrix from a collection of ExtractedFacts."""
        # Filter to quantitative facts with values and fiscal years
        numeric_facts = [f for f in facts if f.value is not None and f.fiscal_year is not None]

        companies = sorted(list({f.company for f in numeric_facts}))
        fiscal_years = sorted(list({f.fiscal_year for f in numeric_facts if f.fiscal_year is not None}), reverse=True)

        # Detect fiscal calendar end-month differences
        calendar_warnings: list[str] = []
        company_end_dates: dict[str, set[str]] = {}
        for f in numeric_facts:
            if f.period_end:
                company_end_dates.setdefault(f.company, set()).add(f.period_end)

        end_months: dict[str, int] = {}
        for comp, p_ends in company_end_dates.items():
            months = [int(p.split("-")[1]) for p in p_ends if len(p.split("-")) >= 2]
            if months:
                end_months[comp] = max(set(months), key=months.count)

        if len(end_months) > 1:
            month_names = {
                1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
            }
            details = [f"{comp} ({month_names.get(m, str(m))})" for comp, m in end_months.items()]
            calendar_warnings.append(
                f"Fiscal Year Calendar Mismatch: Companies have non-aligned fiscal year-ends: {', '.join(details)}. "
                "Direct annual comparisons reflect periods ending several months apart."
            )

        # Group facts by canonical metric name
        metric_groups: dict[str, list[ExtractedFact]] = {}
        for f in numeric_facts:
            metric_title = _clean_metric_title(f.xbrl_tag or f.claim)
            metric_groups.setdefault(metric_title, []).append(f)

        rows: list[AlignedMetricRow] = []
        for metric_title, group in metric_groups.items():
            row = AlignedMetricRow(metric_name=metric_title)
            for f in group:
                if f.fiscal_year is not None:
                    cell = MetricCell(
                        company=f.company,
                        fiscal_year=f.fiscal_year,
                        value=f.value,
                        formatted_value=_format_cell_value(f.value, f.unit),
                        unit=f.unit,
                        fact=f,
                    )
                    row.cells[(f.company, f.fiscal_year)] = cell
            rows.append(row)

        return AlignmentMatrix(
            companies=companies,
            fiscal_years=fiscal_years,
            rows=rows,
            calendar_warnings=calendar_warnings,
        )
