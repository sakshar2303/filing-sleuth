"""
Filing Sleuth — Forensic Red Flag Radar & Accounting Quality Engine

Performs deterministic accounting forensics on extracted SEC XBRL facts:
1. Accrual Quality Gap: (Net Income - Operating Cash Flow) / Total Assets
   - Detects when earnings are driven by non-cash accounting adjustments rather than cash receipts.
2. Days Sales Outstanding (DSO): (Accounts Receivable / Revenue) * 365
   - Flags aggressive revenue recognition, pulled-forward sales, or deteriorating collection velocity.
3. Balance Sheet Solvency & Leverage: Total Liabilities / Total Assets & Working Capital
   - Evaluates financial buffer and solvency risk.
4. Composite Forensic Health Score (0–100):
   - 80–100: Pristine / High Earnings Quality (Low Risk 🟢)
   - 50–79: Moderate Quality / Gray Zone (Caution 🟡)
   - 0–49: Elevated Risk / Accounting Anomalies (Red Flag 🔴)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.agent.extraction_agent import ExtractedFact

logger = logging.getLogger(__name__)


@dataclass
class ForensicMetric:
    """An individual forensic accounting diagnostic indicator."""
    metric_id: str             # e.g., "ACCRUAL_GAP", "DSO", "LEVERAGE"
    name: str                  # e.g., "Earnings Cash Backing"
    category: str              # "EARNINGS_QUALITY", "REVENUE_RECOGNITION", "SOLVENCY"
    status: str                # "PASS", "WARNING", "ALERT"
    score: int                 # 0 to 100
    display_value: str         # e.g., "-0.04 (Cash-Backed)"
    formula: str               # e.g., "(Net Income - Operating Cash Flow) / Total Assets"
    description: str
    operands: dict[str, Any] = field(default_factory=dict)


@dataclass
class ForensicScorecard:
    """A comprehensive forensic health assessment for a company and fiscal period."""
    company: str
    fiscal_year: int | None
    overall_score: int         # 0 to 100
    risk_level: str            # "LOW_RISK", "GRAY_ZONE", "HIGH_RISK"
    status_label: str          # e.g., "Pristine Earnings Quality", "Elevated Caution"
    metrics: list[ForensicMetric] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    positive_signals: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "company": self.company,
            "fiscal_year": self.fiscal_year,
            "overall_score": self.overall_score,
            "risk_level": self.risk_level,
            "status_label": self.status_label,
            "metrics": [
                {
                    "metric_id": m.metric_id,
                    "name": m.name,
                    "category": m.category,
                    "status": m.status,
                    "score": m.score,
                    "display_value": m.display_value,
                    "formula": m.formula,
                    "description": m.description,
                    "operands": m.operands,
                }
                for m in self.metrics
            ],
            "red_flags": self.red_flags,
            "positive_signals": self.positive_signals,
            "summary": self.summary,
        }


class ForensicRadarEngine:
    """Calculates deterministic forensic accounting diagnostics from SEC facts."""

    def evaluate_company(
        self,
        company: str,
        facts: list[ExtractedFact],
        fiscal_year: int | None = None,
    ) -> ForensicScorecard | None:
        """Analyze extracted facts for a given company and generate a ForensicScorecard."""
        comp_facts = [f for f in facts if f.company.upper() == company.upper()]
        if not comp_facts:
            return None

        # Determine target fiscal year if not provided
        if fiscal_year is None:
            years = [f.fiscal_year for f in comp_facts if f.fiscal_year is not None]
            fiscal_year = max(years) if years else None

        # Filter facts for this fiscal year or latest available
        year_facts = [f for f in comp_facts if f.fiscal_year == fiscal_year] if fiscal_year else comp_facts

        # Helper to find tag value
        def find_val(keywords: list[str]) -> tuple[float | None, str | None]:
            for f in year_facts:
                if f.value is not None and f.xbrl_tag:
                    for kw in keywords:
                        if kw.lower() in f.xbrl_tag.lower():
                            return f.value, f.xbrl_tag
            return None, None

        # Search for core US-GAAP line items
        rev, rev_tag = find_val(["RevenueFromContractWithCustomer", "Revenues", "SalesRevenueNet", "Revenue"])
        net_inc, net_tag = find_val(["NetIncomeLoss", "ProfitLoss", "NetIncome"])
        ocf, ocf_tag = find_val(["NetCashProvidedByUsedInOperatingActivities", "OperatingCashFlow", "OperatingActivities"])
        assets, assets_tag = find_val(["Assets", "TotalAssets"])
        ar, ar_tag = find_val(["AccountsReceivableNetCurrent", "AccountsReceivable", "ReceivablesNetCurrent"])
        liab, liab_tag = find_val(["Liabilities", "LiabilitiesAndStockholdersEquity", "TotalLiabilities"])

        return self._compute_metrics_and_scorecard(
            company=company,
            fiscal_year=fiscal_year,
            rev=rev, rev_tag=rev_tag,
            net_inc=net_inc, net_tag=net_tag,
            ocf=ocf, ocf_tag=ocf_tag,
            assets=assets, assets_tag=assets_tag,
            ar=ar, ar_tag=ar_tag,
            liab=liab, liab_tag=liab_tag,
        )

    def evaluate_from_raw_facts(
        self,
        company: str,
        raw_company_facts: dict[str, Any],
        fiscal_year: int | None = None,
    ) -> ForensicScorecard | None:
        """Evaluate forensic scorecard directly from data.sec.gov CompanyFacts JSON."""
        us_gaap = raw_company_facts.get("facts", {}).get("us-gaap", {})
        if not us_gaap:
            return None

        def get_concept_val(concepts: list[str]) -> tuple[float | None, str | None]:
            for c in concepts:
                if c in us_gaap:
                    units = us_gaap[c].get("units", {}).get("USD", [])
                    entries = [e for e in units if e.get("form") in ["10-K", "10-K/A"]]
                    if fiscal_year:
                        entries = [e for e in entries if e.get("fy") == fiscal_year]
                    if entries:
                        sorted_entries = sorted(entries, key=lambda x: x.get("end", ""), reverse=True)
                        val = sorted_entries[0].get("val")
                        if val is not None:
                            return float(val), c
            return None, None

        rev, rev_tag = get_concept_val(["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"])
        net_inc, net_tag = get_concept_val(["NetIncomeLoss", "ProfitLoss", "NetIncome"])
        ocf, ocf_tag = get_concept_val(["NetCashProvidedByUsedInOperatingActivities", "OperatingCashFlow"])
        assets, assets_tag = get_concept_val(["Assets", "TotalAssets"])
        ar, ar_tag = get_concept_val(["AccountsReceivableNetCurrent", "ReceivablesNetCurrent", "AccountsReceivable"])
        liab, liab_tag = get_concept_val(["Liabilities", "LiabilitiesAndStockholdersEquity"])

        return self._compute_metrics_and_scorecard(
            company=company,
            fiscal_year=fiscal_year,
            rev=rev, rev_tag=rev_tag,
            net_inc=net_inc, net_tag=net_tag,
            ocf=ocf, ocf_tag=ocf_tag,
            assets=assets, assets_tag=assets_tag,
            ar=ar, ar_tag=ar_tag,
            liab=liab, liab_tag=liab_tag,
        )

    def _compute_metrics_and_scorecard(
        self,
        company: str,
        fiscal_year: int | None,
        rev: float | None,
        rev_tag: str | None,
        net_inc: float | None,
        net_tag: str | None,
        ocf: float | None,
        ocf_tag: str | None,
        assets: float | None,
        assets_tag: str | None,
        ar: float | None,
        ar_tag: str | None,
        liab: float | None,
        liab_tag: str | None,
    ) -> ForensicScorecard | None:
        """Compute forensic metrics and composite scorecard from line item values."""
        metrics: list[ForensicMetric] = []
        red_flags: list[str] = []
        positive_signals: list[str] = []

        # 1. Earnings Quality / Accrual Gap
        if net_inc is not None and ocf is not None:
            base_assets = assets if (assets and assets > 0) else (rev if (rev and rev > 0) else 1e10)
            accrual_gap = (net_inc - ocf) / base_assets
            
            if accrual_gap <= -0.02:
                status = "PASS"
                score = 95
                disp = f"{accrual_gap:+.2f} (Cash > Net Income)"
                desc = "Operating cash flow comfortably exceeds reported net income, indicating conservative and high-quality earnings."
                positive_signals.append(f"High cash conversion: Operating cash flow exceeded net income by ${abs(ocf - net_inc):,.0f}.")
            elif accrual_gap <= 0.05:
                status = "PASS"
                score = 85
                disp = f"{accrual_gap:+.2f} (Balanced)"
                desc = "Net income is closely aligned with operating cash receipts with minimal non-cash accrual inflation."
                positive_signals.append("Net income is well-supported by underlying cash generation.")
            elif accrual_gap <= 0.12:
                status = "WARNING"
                score = 60
                disp = f"{accrual_gap:+.2f} (Moderate Accrual)"
                desc = "Net income exceeds operating cash flow; a moderate portion of earnings stems from accounting accruals."
                red_flags.append(f"Net income exceeds operating cash flow by ${net_inc - ocf:,.0f} (moderate accrual drag).")
            else:
                status = "ALERT"
                score = 30
                disp = f"{accrual_gap:+.2f} (High Accrual Lag)"
                desc = "Significant divergence: Reported net income is heavily reliant on non-cash accounting gains rather than cash from customers."
                red_flags.append(f"Substantial cash-to-net-income shortfall: ${net_inc - ocf:,.0f} gap relative to balance sheet size.")

            metrics.append(
                ForensicMetric(
                    metric_id="ACCRUAL_GAP",
                    name="Earnings Cash Backing",
                    category="EARNINGS_QUALITY",
                    status=status,
                    score=score,
                    display_value=disp,
                    formula="(Net Income - Operating Cash Flow) / Total Assets",
                    description=desc,
                    operands={
                        "net_income": {"value": net_inc, "tag": net_tag},
                        "operating_cash_flow": {"value": ocf, "tag": ocf_tag},
                        "assets": {"value": assets, "tag": assets_tag},
                    },
                )
            )

        # 2. Days Sales Outstanding (DSO) & Receivables Intensity
        if ar is not None and rev is not None and rev > 0:
            dso = (ar / rev) * 365.0
            if dso <= 45:
                status = "PASS"
                score = 92
                disp = f"{dso:.1f} Days (Rapid Collection)"
                desc = f"Average customer collection cycle is {dso:.1f} days, indicating strong working capital discipline and low channel credit risk."
                positive_signals.append(f"Rapid receivables conversion cycle ({dso:.1f} days).")
            elif dso <= 75:
                status = "PASS"
                score = 80
                disp = f"{dso:.1f} Days (Standard Normal)"
                desc = f"Receivables velocity of {dso:.1f} days is well within normal corporate payment terms."
            elif dso <= 105:
                status = "WARNING"
                score = 55
                disp = f"{dso:.1f} Days (Extended DSO)"
                desc = f"Collection cycle of {dso:.1f} days indicates customer credit elongation or potential pull-forward of quarterly revenue."
                red_flags.append(f"Extended collection cycle ({dso:.1f} days DSO) flags potential revenue pull-forwards.")
            else:
                status = "ALERT"
                score = 35
                disp = f"{dso:.1f} Days (Critical DSO Spurt)"
                desc = f"High collection latency ({dso:.1f} days). Significantly increases the probability of future bad-debt write-downs or channel stuffing."
                red_flags.append(f"High Days Sales Outstanding ({dso:.1f} days) suggests aggressive revenue recognition terms.")

            metrics.append(
                ForensicMetric(
                    metric_id="DSO",
                    name="Receivables Velocity (DSO)",
                    category="REVENUE_RECOGNITION",
                    status=status,
                    score=score,
                    display_value=disp,
                    formula="(Accounts Receivable / Revenue) * 365",
                    description=desc,
                    operands={
                        "accounts_receivable": {"value": ar, "tag": ar_tag},
                        "revenue": {"value": rev, "tag": rev_tag},
                    },
                )
            )

        # 3. Solvency & Debt Leverage Ratio
        if liab is not None and assets is not None and assets > 0:
            leverage = liab / assets
            if leverage <= 0.45:
                status = "PASS"
                score = 95
                disp = f"{leverage * 100:.1f}% (Conservative)"
                desc = "Fortress balance sheet with liabilities well under half of total asset value. Minimal refinancing or insolvency risk."
                positive_signals.append(f"Conservative balance sheet leverage ({leverage * 100:.1f}% total liabilities to assets).")
            elif leverage <= 0.70:
                status = "PASS"
                score = 82
                disp = f"{leverage * 100:.1f}% (Moderate Leverage)"
                desc = "Standard capital structure with manageable leverage against corporate assets."
            elif leverage <= 0.88:
                status = "WARNING"
                score = 55
                disp = f"{leverage * 100:.1f}% (Elevated Debt)"
                desc = "Elevated liabilities-to-assets ratio; interest expense and refinancing vulnerability requires scrutiny."
                red_flags.append(f"Elevated total liability load ({leverage * 100:.1f}% of assets).")
            else:
                status = "ALERT"
                score = 30
                disp = f"{leverage * 100:.1f}% (Highly Leveraged)"
                desc = "Thin equity cushion. Liabilities absorb nearly all reported assets, exposing the company to covenant pressures."
                red_flags.append(f"Very thin equity cushion: liabilities represent {leverage * 100:.1f}% of total assets.")

            metrics.append(
                ForensicMetric(
                    metric_id="LEVERAGE",
                    name="Balance Sheet Leverage",
                    category="SOLVENCY",
                    status=status,
                    score=score,
                    display_value=disp,
                    formula="Total Liabilities / Total Assets",
                    description=desc,
                    operands={
                        "total_liabilities": {"value": liab, "tag": liab_tag},
                        "total_assets": {"value": assets, "tag": assets_tag},
                    },
                )
            )

        # If minimal metrics were extracted, compute synthetic baseline from available data
        if not metrics:
            return None

        # Compute weighted overall score
        total_score = sum(m.score for m in metrics)
        overall_score = round(total_score / len(metrics))

        if overall_score >= 80:
            risk_level = "LOW_RISK"
            status_label = "Pristine Earnings Quality"
            summary = (
                f"{company}'s financial reporting displays high integrity. "
                "Operating cash flow comfortably validates net income, receivables velocity is disciplined, "
                "and balance sheet solvency reflects robust risk protection."
            )
        elif overall_score >= 55:
            risk_level = "GRAY_ZONE"
            status_label = "Moderate Caution (Gray Zone)"
            summary = (
                f"{company}'s metrics fall within acceptable parameters but warrant ongoing monitoring. "
                "Minor divergence between cash flows and non-cash accruals observed."
            )
        else:
            risk_level = "HIGH_RISK"
            status_label = "Elevated Forensic Red Flags"
            summary = (
                f"Forensic signals indicate elevated accounting vulnerability for {company}. "
                "A significant disparity exists between reported accounting gains and underlying cash collection."
            )

        return ForensicScorecard(
            company=company,
            fiscal_year=fiscal_year,
            overall_score=overall_score,
            risk_level=risk_level,
            status_label=status_label,
            metrics=metrics,
            red_flags=red_flags,
            positive_signals=positive_signals,
            summary=summary,
        )
