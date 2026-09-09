"""
Filing Sleuth — Financial Dossier & Multi-Year Statement Analytics Engine

Extracts standardized multi-year historical financial series (Income Statement,
Cash Flow, Balance Sheet, Margins, and Growth Rates) directly from SEC CompanyFacts XBRL.
Computes deterministic multi-year KPIs, CAGRs, margin profiles, and cash conversion ratios
to power institutional-grade research memos and interactive financial charts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from backend.agent.extraction_agent import ExtractedFact
from backend.crossref.computations import ComputedResult

logger = logging.getLogger(__name__)


# Standard US-GAAP concept mappings in order of reporting preference
CONCEPT_TAG_CANDIDATES: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "net_income": [
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncome",
    ],
    "gross_profit": [
        "GrossProfit",
    ],
    "operating_income": [
        "OperatingIncomeLoss",
    ],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "OperatingCashFlow",
    ],
    "rd_expense": [
        "ResearchAndDevelopmentExpense",
        "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
    "assets": [
        "Assets",
        "TotalAssets",
    ],
    "liabilities": [
        "Liabilities",
        "TotalLiabilities",
    ],
}


class AnnualFinancialSnapshot(BaseModel):
    """Normalized financial performance data for a single fiscal year."""
    fiscal_year: int
    revenue: float | None = None
    net_income: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    operating_cash_flow: float | None = None
    rd_expense: float | None = None
    capex: float | None = None
    assets: float | None = None
    liabilities: float | None = None

    # Calculated ratios
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    rd_intensity: float | None = None
    free_cash_flow: float | None = None
    cash_conversion_pct: float | None = None
    debt_to_assets_pct: float | None = None
    yoy_revenue_growth_pct: float | None = None
    yoy_net_income_growth_pct: float | None = None

    # Source filing accession
    accession_number: str | None = None


class CompanyFinancialDossier(BaseModel):
    """Institutional-grade financial dossier containing multi-year series and KPIs."""
    company_ticker: str
    company_name: str
    cik: str
    fiscal_years: list[int] = Field(default_factory=list)
    series: list[AnnualFinancialSnapshot] = Field(default_factory=list)
    summary_kpis: dict[str, Any] = Field(default_factory=dict)
    chart_payload: dict[str, Any] = Field(default_factory=dict)


class FinancialDossierEngine:
    """Extracts and computes multi-year financial statement dossiers from raw XBRL facts."""

    def extract_dossier(
        self,
        company_ticker: str,
        company_name: str,
        cik: str,
        raw_facts: dict[str, Any],
        max_years: int = 5,
    ) -> tuple[CompanyFinancialDossier, list[ExtractedFact], list[ComputedResult]]:
        """Build full multi-year dossier, extracted facts list, and computed result derivations."""
        us_gaap = raw_facts.get("facts", {}).get("us-gaap", {})
        if not us_gaap:
            return CompanyFinancialDossier(
                company_ticker=company_ticker,
                company_name=company_name,
                cik=cik,
            ), [], []

        # 1. Extract annual data per metric
        raw_metric_data: dict[str, dict[int, dict[str, Any]]] = {}
        for metric_name, tag_candidates in CONCEPT_TAG_CANDIDATES.items():
            for tag in tag_candidates:
                concept_obj = us_gaap.get(tag)
                if not concept_obj:
                    continue
                units = concept_obj.get("units", {}).get("USD", [])
                # Filter strictly to official 10-K full fiscal year filings
                annual_entries = [
                    e for e in units
                    if e.get("form") in ("10-K", "10-K/A") and e.get("fp") == "FY"
                ]
                if not annual_entries:
                    continue

                by_fy: dict[int, dict[str, Any]] = {}
                for entry in sorted(annual_entries, key=lambda x: x.get("end", "")):
                    fy = entry.get("fy")
                    if fy and isinstance(fy, int) and 2015 <= fy <= 2030:
                        by_fy[fy] = {
                            "val": float(entry.get("val", 0)),
                            "accn": entry.get("accn"),
                            "tag": tag,
                            "filed": entry.get("filed"),
                        }

                if by_fy:
                    raw_metric_data[metric_name] = by_fy
                    break

        # 2. Determine target fiscal years (last max_years years available in revenue or net_income)
        all_years = set()
        for metric_map in raw_metric_data.values():
            all_years.update(metric_map.keys())

        sorted_years = sorted(all_years)[-max_years:]
        if not sorted_years:
            return CompanyFinancialDossier(
                company_ticker=company_ticker,
                company_name=company_name,
                cik=cik,
            ), [], []

        # 3. Assemble AnnualFinancialSnapshot for each year
        series: list[AnnualFinancialSnapshot] = []
        extra_facts: list[ExtractedFact] = []
        computed_derivations: list[ComputedResult] = []

        prev_snap: AnnualFinancialSnapshot | None = None
        for fy in sorted_years:
            rev_info = raw_metric_data.get("revenue", {}).get(fy)
            net_info = raw_metric_data.get("net_income", {}).get(fy)
            gross_info = raw_metric_data.get("gross_profit", {}).get(fy)
            op_inc_info = raw_metric_data.get("operating_income", {}).get(fy)
            ocf_info = raw_metric_data.get("operating_cash_flow", {}).get(fy)
            rd_info = raw_metric_data.get("rd_expense", {}).get(fy)
            capex_info = raw_metric_data.get("capex", {}).get(fy)
            assets_info = raw_metric_data.get("assets", {}).get(fy)
            liab_info = raw_metric_data.get("liabilities", {}).get(fy)

            rev = rev_info["val"] if rev_info else None
            net = net_info["val"] if net_info else None
            gross = gross_info["val"] if gross_info else None
            op_inc = op_inc_info["val"] if op_inc_info else None
            ocf = ocf_info["val"] if ocf_info else None
            rd = rd_info["val"] if rd_info else None
            capex = capex_info["val"] if capex_info else None
            assets = assets_info["val"] if assets_info else None
            liab = liab_info["val"] if liab_info else None

            # Primary accession for citation
            accn = (
                (rev_info and rev_info.get("accn"))
                or (net_info and net_info.get("accn"))
                or (ocf_info and ocf_info.get("accn"))
            )

            # Ratios
            gross_margin = round((gross / rev) * 100.0, 2) if (gross is not None and rev and rev > 0) else None
            operating_margin = round((op_inc / rev) * 100.0, 2) if (op_inc is not None and rev and rev > 0) else None
            net_margin = round((net / rev) * 100.0, 2) if (net is not None and rev and rev > 0) else None
            rd_intensity = round((rd / rev) * 100.0, 2) if (rd is not None and rev and rev > 0) else None
            fcf = round(ocf - capex, 2) if (ocf is not None and capex is not None) else (ocf if ocf is not None else None)
            cash_conv = round((ocf / net) * 100.0, 1) if (ocf is not None and net and net > 0) else None
            debt_assets = round((liab / assets) * 100.0, 1) if (liab is not None and assets and assets > 0) else None

            # Growth deltas vs previous year
            yoy_rev_pct = None
            if prev_snap and prev_snap.revenue and rev:
                yoy_rev_pct = round(((rev - prev_snap.revenue) / prev_snap.revenue) * 100.0, 2)
            yoy_net_pct = None
            if prev_snap and prev_snap.net_income and net:
                yoy_net_pct = round(((net - prev_snap.net_income) / abs(prev_snap.net_income)) * 100.0, 2)

            snapshot = AnnualFinancialSnapshot(
                fiscal_year=fy,
                revenue=rev,
                net_income=net,
                gross_profit=gross,
                operating_income=op_inc,
                operating_cash_flow=ocf,
                rd_expense=rd,
                capex=capex,
                assets=assets,
                liabilities=liab,
                gross_margin=gross_margin,
                operating_margin=operating_margin,
                net_margin=net_margin,
                rd_intensity=rd_intensity,
                free_cash_flow=fcf,
                cash_conversion_pct=cash_conv,
                debt_to_assets_pct=debt_assets,
                yoy_revenue_growth_pct=yoy_rev_pct,
                yoy_net_income_growth_pct=yoy_net_pct,
                accession_number=accn,
            )
            series.append(snapshot)
            prev_snap = snapshot

            # Generate formal ExtractedFact entries for key metrics so pipeline alignment has them
            if rev is not None and rev_info:
                extra_facts.append(
                    ExtractedFact(
                        sub_question_id=f"dossier_rev_{fy}",
                        company=company_name or company_ticker,
                        cik=cik,
                        accession_number=rev_info["accn"],
                        fiscal_year=fy,
                        fiscal_period="FY",
                        value=rev,
                        unit="USD",
                        status="FOUND",
                        source_type="XBRL",
                        xbrl_tag=f"us-gaap:{rev_info['tag']}",
                        claim=f"{company_name or company_ticker} reported Revenue of ${rev:,.0f} for FY{fy}.",
                    )
                )

            if net is not None and net_info:
                extra_facts.append(
                    ExtractedFact(
                        sub_question_id=f"dossier_net_{fy}",
                        company=company_name or company_ticker,
                        cik=cik,
                        accession_number=net_info["accn"],
                        fiscal_year=fy,
                        fiscal_period="FY",
                        value=net,
                        unit="USD",
                        status="FOUND",
                        source_type="XBRL",
                        xbrl_tag=f"us-gaap:{net_info['tag']}",
                        claim=f"{company_name or company_ticker} reported Net Income of ${net:,.0f} for FY{fy}.",
                    )
                )

            if ocf is not None and ocf_info:
                extra_facts.append(
                    ExtractedFact(
                        sub_question_id=f"dossier_ocf_{fy}",
                        company=company_name or company_ticker,
                        cik=cik,
                        accession_number=ocf_info["accn"],
                        fiscal_year=fy,
                        fiscal_period="FY",
                        value=ocf,
                        unit="USD",
                        status="FOUND",
                        source_type="XBRL",
                        xbrl_tag=f"us-gaap:{ocf_info['tag']}",
                        claim=f"{company_name or company_ticker} generated Operating Cash Flow of ${ocf:,.0f} for FY{fy}.",
                    )
                )

            # Generate ComputedResults for margins
            if operating_margin is not None and op_inc is not None and rev:
                computed_derivations.append(
                    ComputedResult(
                        computation_type="MARGIN_RATIO",
                        metric_label="Operating Margin",
                        company=company_name or company_ticker,
                        fiscal_year=fy,
                        result_value=operating_margin,
                        result_formatted=f"{operating_margin:.2f}%",
                        formula=f"(${op_inc:,.0f} / ${rev:,.0f}) * 100",
                        inputs=[
                            {"role": "numerator", "label": "Operating Income", "value": op_inc},
                            {"role": "denominator", "label": "Revenue", "value": rev},
                        ],
                        description=f"{company_name or company_ticker}'s Operating Margin was {operating_margin:.2f}% in FY{fy}.",
                    )
                )

            if yoy_rev_pct is not None:
                computed_derivations.append(
                    ComputedResult(
                        computation_type="YOY_GROWTH",
                        metric_label="Revenue YoY Growth",
                        company=company_name or company_ticker,
                        fiscal_year=fy,
                        result_value=yoy_rev_pct,
                        result_formatted=f"{yoy_rev_pct:+.2f}%",
                        formula=f"((${rev:,.0f} - ${prev_snap.revenue:,.0f}) / ${prev_snap.revenue:,.0f}) * 100",
                        inputs=[
                            {"role": "current", "label": f"FY{fy} Revenue", "value": rev},
                            {"role": "previous", "label": f"FY{fy-1} Revenue", "value": prev_snap.revenue},
                        ],
                        description=f"{company_name or company_ticker}'s Revenue grew {yoy_rev_pct:+.2f}% YoY in FY{fy}.",
                    )
                )

        # 4. Summary Executive KPIs
        latest = series[-1] if series else None
        oldest = series[0] if series else None

        # 3-Year CAGR if at least 3 years available
        cagr_rev = None
        if latest and oldest and len(series) >= 3 and oldest.revenue and latest.revenue and oldest.revenue > 0:
            n_years = latest.fiscal_year - oldest.fiscal_year
            if n_years > 0:
                cagr_rev = round((((latest.revenue / oldest.revenue) ** (1.0 / n_years)) - 1.0) * 100.0, 2)

        summary_kpis = {
            "company": company_name or company_ticker,
            "ticker": company_ticker,
            "latest_fiscal_year": latest.fiscal_year if latest else None,
            "latest_revenue": latest.revenue if latest else None,
            "latest_revenue_formatted": self._format_currency(latest.revenue) if latest else "N/A",
            "latest_net_income": latest.net_income if latest else None,
            "latest_net_income_formatted": self._format_currency(latest.net_income) if latest else "N/A",
            "latest_operating_margin": latest.operating_margin if latest else None,
            "latest_gross_margin": latest.gross_margin if latest else None,
            "latest_net_margin": latest.net_margin if latest else None,
            "yoy_revenue_growth_pct": latest.yoy_revenue_growth_pct if latest else None,
            "yoy_net_income_growth_pct": latest.yoy_net_income_growth_pct if latest else None,
            "three_year_cagr_revenue_pct": cagr_rev,
            "latest_cash_conversion_pct": latest.cash_conversion_pct if latest else None,
            "latest_debt_to_assets_pct": latest.debt_to_assets_pct if latest else None,
        }

        # 5. Build structured chart payload
        chart_payload = {
            "company": company_name or company_ticker,
            "ticker": company_ticker,
            "years": sorted_years,
            "series": [s.model_dump() for s in series],
            "summary_kpis": summary_kpis,
        }

        dossier = CompanyFinancialDossier(
            company_ticker=company_ticker,
            company_name=company_name or company_ticker,
            cik=cik,
            fiscal_years=sorted_years,
            series=series,
            summary_kpis=summary_kpis,
            chart_payload=chart_payload,
        )

        return dossier, extra_facts, computed_derivations

    @staticmethod
    def _format_currency(val: float | None) -> str:
        if val is None:
            return "N/A"
        sign = "-" if val < 0 else ""
        abs_v = abs(val)
        if abs_v >= 1e12:
            return f"{sign}${abs_v / 1e12:.2f}T"
        if abs_v >= 1e9:
            return f"{sign}${abs_v / 1e9:.2f}B"
        if abs_v >= 1e6:
            return f"{sign}${abs_v / 1e6:.2f}M"
        return f"{sign}${abs_v:,.0f}"
