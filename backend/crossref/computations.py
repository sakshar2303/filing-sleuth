"""
Filing Sleuth — Financial Computations Engine

Performs deterministic math on extracted facts:
- Margin ratios (R&D % of Revenue, Operating Margin, Net Margin)
- Period-over-Period growth rates (YoY dollar delta and percentage change)
- Peer spread comparisons (Company A metric minus Company B metric)
- Full mathematical provenance (records formula, input operands, and units)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.agent.extraction_agent import ExtractedFact
from backend.crossref.alignment import AlignmentMatrix

logger = logging.getLogger(__name__)


@dataclass
class ComputedResult:
    """A calculated financial metric with full derivation provenance."""
    computation_type: str        # "MARGIN_RATIO", "YOY_GROWTH", "PEER_SPREAD"
    metric_label: str            # e.g., "R&D as % of Revenue"
    company: str
    fiscal_year: int | None
    result_value: float
    result_formatted: str        # e.g., "8.30%"
    formula: str                 # e.g., "(34.55B / 416.16B) * 100"
    inputs: list[dict[str, Any]] # Operand facts and values
    description: str


class FinancialComputations:
    """Computes margins, YoY growth, and cross-company comparisons."""

    def compute_all(
        self,
        facts: list[ExtractedFact],
        matrix: AlignmentMatrix | None = None,
    ) -> list[ComputedResult]:
        """Run all applicable calculations over the extracted facts."""
        results: list[ComputedResult] = []

        # 1. Compute Margin Ratios (e.g. R&D % of Revenue, Net Margin)
        results.extend(self.compute_margins(facts))

        # 2. Compute YoY Growth rates for each metric across consecutive years
        results.extend(self.compute_yoy_growth(facts))

        # 3. Compute Peer Spreads if multiple companies exist
        results.extend(self.compute_peer_spreads(results))

        return results

    def compute_margins(self, facts: list[ExtractedFact]) -> list[ComputedResult]:
        """Compute margin ratios (e.g. R&D / Revenue, Operating Margin, Net Margin)."""
        computed: list[ComputedResult] = []

        # Group facts by (company, fiscal_year)
        by_comp_year: dict[tuple[str, int], list[ExtractedFact]] = {}
        for f in facts:
            if f.value is not None and f.fiscal_year is not None:
                by_comp_year.setdefault((f.company, f.fiscal_year), []).append(f)

        for (comp, year), comp_facts in by_comp_year.items():
            rev_fact = next(
                (f for f in comp_facts if f.xbrl_tag and ("Revenue" in f.xbrl_tag or "Sales" in f.xbrl_tag)),
                None,
            )
            if not rev_fact or not rev_fact.value:
                continue

            # R&D % of Revenue
            rd_fact = next(
                (f for f in comp_facts if f.xbrl_tag and "ResearchAndDevelopment" in f.xbrl_tag),
                None,
            )
            if rd_fact and rd_fact.value is not None:
                ratio = (rd_fact.value / rev_fact.value) * 100.0
                computed.append(
                    ComputedResult(
                        computation_type="MARGIN_RATIO",
                        metric_label="R&D as % of Revenue",
                        company=comp,
                        fiscal_year=year,
                        result_value=round(ratio, 2),
                        result_formatted=f"{ratio:.2f}%",
                        formula=f"(${rd_fact.value:,.0f} / ${rev_fact.value:,.0f}) * 100",
                        inputs=[
                            {"role": "numerator", "label": "R&D Expense", "value": rd_fact.value, "fact": rd_fact.model_dump()},
                            {"role": "denominator", "label": "Revenue", "value": rev_fact.value, "fact": rev_fact.model_dump()},
                        ],
                        description=f"{comp}'s R&D spend was {ratio:.2f}% of revenue in FY{year}.",
                    )
                )

            # Net Margin
            net_fact = next(
                (f for f in comp_facts if f.xbrl_tag and "NetIncome" in f.xbrl_tag),
                None,
            )
            if net_fact and net_fact.value is not None:
                ratio = (net_fact.value / rev_fact.value) * 100.0
                computed.append(
                    ComputedResult(
                        computation_type="MARGIN_RATIO",
                        metric_label="Net Margin",
                        company=comp,
                        fiscal_year=year,
                        result_value=round(ratio, 2),
                        result_formatted=f"{ratio:.2f}%",
                        formula=f"(${net_fact.value:,.0f} / ${rev_fact.value:,.0f}) * 100",
                        inputs=[
                            {"role": "numerator", "label": "Net Income", "value": net_fact.value, "fact": net_fact.model_dump()},
                            {"role": "denominator", "label": "Revenue", "value": rev_fact.value, "fact": rev_fact.model_dump()},
                        ],
                        description=f"{comp}'s net profit margin was {ratio:.2f}% in FY{year}.",
                    )
                )

        return computed

    def compute_yoy_growth(self, facts: list[ExtractedFact]) -> list[ComputedResult]:
        """Compute Year-over-Year (YoY) growth rates for numeric metrics."""
        computed: list[ComputedResult] = []

        # Group facts by (company, concept/metric)
        by_comp_metric: dict[tuple[str, str], list[ExtractedFact]] = {}
        for f in facts:
            if f.value is not None and f.fiscal_year is not None and f.xbrl_tag:
                by_comp_metric.setdefault((f.company, f.xbrl_tag), []).append(f)

        for (comp, tag), metric_facts in by_comp_metric.items():
            # Sort descending by year
            sorted_facts = sorted(metric_facts, key=lambda f: f.fiscal_year or 0, reverse=True)

            for i in range(len(sorted_facts) - 1):
                f_curr = sorted_facts[i]
                f_prev = sorted_facts[i + 1]

                if f_curr.fiscal_year is None or f_prev.fiscal_year is None:
                    continue
                # Only compare consecutive years
                if f_curr.fiscal_year - f_prev.fiscal_year != 1:
                    continue
                if not f_prev.value or f_prev.value == 0:
                    continue

                delta_dollars = f_curr.value - f_prev.value
                pct_growth = (delta_dollars / abs(f_prev.value)) * 100.0
                sign = "+" if pct_growth >= 0 else ""

                short_tag = tag.split(":")[-1]
                computed.append(
                    ComputedResult(
                        computation_type="YOY_GROWTH",
                        metric_label=f"{short_tag} YoY Growth",
                        company=comp,
                        fiscal_year=f_curr.fiscal_year,
                        result_value=round(pct_growth, 2),
                        result_formatted=f"{sign}{pct_growth:.2f}%",
                        formula=f"((${f_curr.value:,.0f} - ${f_prev.value:,.0f}) / ${f_prev.value:,.0f}) * 100",
                        inputs=[
                            {"role": "current", "year": f_curr.fiscal_year, "value": f_curr.value},
                            {"role": "previous", "year": f_prev.fiscal_year, "value": f_prev.value},
                        ],
                        description=f"{comp}'s {short_tag} grew {sign}{pct_growth:.2f}% YoY in FY{f_curr.fiscal_year}.",
                    )
                )

        return computed

    def compute_peer_spreads(self, margin_results: list[ComputedResult]) -> list[ComputedResult]:
        """Compute the spread/difference between two peer companies on same metric and year."""
        computed: list[ComputedResult] = []

        # Group margins by (metric_label, fiscal_year)
        by_metric_year: dict[tuple[str, int | None], list[ComputedResult]] = {}
        for r in margin_results:
            if r.computation_type == "MARGIN_RATIO":
                by_metric_year.setdefault((r.metric_label, r.fiscal_year), []).append(r)

        for (metric_label, year), results_list in by_metric_year.items():
            if len(results_list) >= 2:
                # Compare first two companies
                r1, r2 = results_list[0], results_list[1]
                spread = r1.result_value - r2.result_value
                sign = "+" if spread >= 0 else ""
                comp_pair = f"{r1.company} vs {r2.company}"

                computed.append(
                    ComputedResult(
                        computation_type="PEER_SPREAD",
                        metric_label=f"{metric_label} Peer Spread",
                        company=comp_pair,
                        fiscal_year=year,
                        result_value=round(spread, 2),
                        result_formatted=f"{sign}{spread:.2f} bps" if abs(spread) < 1 else f"{sign}{spread:.2f}%",
                        formula=f"{r1.result_value:.2f}% - {r2.result_value:.2f}%",
                        inputs=[
                            {"company": r1.company, "value": r1.result_value},
                            {"company": r2.company, "value": r2.result_value},
                        ],
                        description=f"{r1.company}'s {metric_label} exceeded {r2.company}'s by {sign}{spread:.2f}% in FY{year}.",
                    )
                )

        return computed
