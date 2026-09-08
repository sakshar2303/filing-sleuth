"""
Filing Sleuth — XBRL CompanyFacts API

Wraps data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json to retrieve
structured financial data. This is the GROUND TRUTH for numeric values —
always prefer XBRL over text-parsing from prose.

The API returns every XBRL-tagged fact ever filed by a company, organized by
taxonomy (us-gaap, dei, ifrs-full) and concept. Each fact includes:
  - val: the numeric value
  - accn: accession number of the filing
  - fy: fiscal year
  - fp: fiscal period (FY, Q1, Q2, Q3, Q4)
  - form: form type (10-K, 10-Q, 8-K, etc.)
  - filed: date filed
  - frame: the XBRL frame identifier (e.g., CY2023Q3I for a point-in-time,
            CY2023 for a duration)

IMPORTANT: Companies sometimes use custom extension taxonomies instead of
standard us-gaap tags. This module handles that by checking both us-gaap
and the company's custom namespace, and flagging custom tags for manual review.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.retrieval.sec_client import SECClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class XBRLFact:
    """A single XBRL-tagged financial fact."""
    value: float | int
    unit: str                   # "USD", "USD/shares", "shares", "pure" (ratios)
    accession_number: str       # e.g., "0000320193-23-000106"
    fiscal_year: int            # e.g., 2023
    fiscal_period: str          # "FY", "Q1", "Q2", "Q3", "Q4"
    form_type: str              # "10-K", "10-Q", etc.
    filed_date: str             # e.g., "2023-11-03"
    period_end: str             # e.g., "2023-09-30"
    period_start: str | None    # For duration facts; None for point-in-time
    frame: str | None           # XBRL frame identifier
    taxonomy: str               # "us-gaap", "dei", "custom", etc.
    concept: str                # e.g., "Revenues", "ResearchAndDevelopmentExpense"
    label: str                  # Human-readable label from XBRL
    is_custom_tag: bool         # True if not a standard us-gaap/dei tag


# Common financial metrics and their standard us-gaap XBRL tags.
# The query planner uses this mapping to go from natural language → XBRL tag.
COMMON_XBRL_TAGS: dict[str, list[str]] = {
    # Revenue
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
    ],
    # Net income
    "net_income": [
        "NetIncomeLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
        "ProfitLoss",
    ],
    # R&D
    "research_and_development": [
        "ResearchAndDevelopmentExpense",
        "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
    ],
    # Operating income
    "operating_income": [
        "OperatingIncomeLoss",
    ],
    # Gross profit
    "gross_profit": [
        "GrossProfit",
    ],
    # Total assets
    "total_assets": [
        "Assets",
    ],
    # Total liabilities
    "total_liabilities": [
        "Liabilities",
    ],
    # Total debt
    "total_debt": [
        "LongTermDebt",
        "LongTermDebtNoncurrent",
        "DebtCurrent",
        "LongTermDebtAndCapitalLeaseObligations",
    ],
    # Cash
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
    ],
    # EPS
    "earnings_per_share": [
        "EarningsPerShareBasic",
        "EarningsPerShareDiluted",
    ],
    # Shares outstanding
    "shares_outstanding": [
        "CommonStockSharesOutstanding",
        "EntityCommonStockSharesOutstanding",
    ],
    # Cost of revenue
    "cost_of_revenue": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
    ],
    # SG&A
    "selling_general_administrative": [
        "SellingGeneralAndAdministrativeExpense",
    ],
}


class XBRLFactsAPI:
    """Fetch structured financial data from SEC's XBRL CompanyFacts API.

    Usage:
        async with SECClient() as client:
            xbrl = XBRLFactsAPI(client)

            # Get specific metric
            facts = await xbrl.get_facts("0000320193", "Revenues")

            # Get metric by common name
            facts = await xbrl.get_facts_by_common_name("0000320193", "revenue")

            # Get annual-only facts
            annual = [f for f in facts if f.fiscal_period == "FY"]
    """

    def __init__(self, client: SECClient) -> None:
        self.client = client

    async def get_company_facts_raw(self, cik: str) -> dict[str, Any]:
        """Fetch the complete CompanyFacts JSON for a CIK. Cached."""
        url = f"{self.client.settings.sec_data_base}/api/xbrl/companyfacts/CIK{cik}.json"
        return await self.client.get_json(
            url,
            cache_segments=("xbrl", f"CIK{cik}"),
        )

    async def get_facts(
        self,
        cik: str,
        concept: str,
        *,
        taxonomy: str = "us-gaap",
        form_types: list[str] | None = None,
        fiscal_periods: list[str] | None = None,
    ) -> list[XBRLFact]:
        """Extract facts for a specific XBRL concept.

        Args:
            cik: 10-digit zero-padded CIK.
            concept: XBRL concept name (e.g., "Revenues").
            taxonomy: XBRL taxonomy namespace (default: "us-gaap").
            form_types: Filter to these form types (e.g., ["10-K"]). None = all.
            fiscal_periods: Filter to these periods (e.g., ["FY"]). None = all.

        Returns:
            List of XBRLFact objects, sorted by period_end descending (newest first).
        """
        raw = await self.get_company_facts_raw(cik)

        # Navigate the nested structure: facts → {taxonomy} → {concept} → units → {unit} → [entries]
        taxonomy_data = raw.get("facts", {}).get(taxonomy, {})
        is_custom = False

        concept_data = taxonomy_data.get(concept)
        if concept_data is None:
            # Try other taxonomies (companies sometimes use custom namespaces)
            for ns_name, ns_data in raw.get("facts", {}).items():
                if ns_name == taxonomy:
                    continue
                if concept in ns_data:
                    concept_data = ns_data[concept]
                    taxonomy = ns_name
                    is_custom = True
                    logger.info(
                        "Found concept '%s' in custom taxonomy '%s' for CIK %s",
                        concept, taxonomy, cik,
                    )
                    break

        if concept_data is None:
            logger.warning(
                "XBRL concept '%s' not found in any taxonomy for CIK %s",
                concept, cik,
            )
            return []

        label = concept_data.get("label", concept)
        units_data = concept_data.get("units", {})

        facts: list[XBRLFact] = []
        for unit_name, entries in units_data.items():
            for entry in entries:
                form = entry.get("form", "")
                fp = entry.get("fp", "")

                # Apply filters
                if form_types and form not in form_types:
                    continue
                if fiscal_periods and fp not in fiscal_periods:
                    continue

                # Determine if this is a duration or point-in-time fact
                period_start = entry.get("start")
                period_end = entry.get("end", "")

                fact = XBRLFact(
                    value=entry["val"],
                    unit=unit_name,
                    accession_number=entry.get("accn", ""),
                    fiscal_year=entry.get("fy", 0),
                    fiscal_period=fp,
                    form_type=form,
                    filed_date=entry.get("filed", ""),
                    period_end=period_end,
                    period_start=period_start,
                    frame=entry.get("frame"),
                    taxonomy=taxonomy,
                    concept=concept,
                    label=label,
                    is_custom_tag=is_custom,
                )
                facts.append(fact)

        # Sort by period_end descending (newest first)
        facts.sort(key=lambda f: f.period_end, reverse=True)

        logger.info(
            "Found %d XBRL facts for %s:%s (CIK %s), filtered to %s",
            len(facts), taxonomy, concept, cik,
            form_types or "all forms",
        )
        return facts

    async def get_facts_by_common_name(
        self,
        cik: str,
        common_name: str,
        *,
        form_types: list[str] | None = None,
        fiscal_periods: list[str] | None = None,
    ) -> list[XBRLFact]:
        """Look up facts by a common metric name (e.g., "revenue", "net_income").

        Tries each known XBRL tag for the common name until one returns results.
        This handles the fact that different companies may use different
        standard tags for the same concept (e.g., "Revenues" vs
        "RevenueFromContractWithCustomerExcludingAssessedTax").

        Returns facts from the first matching tag, or empty list if none found.
        """
        common_key = common_name.lower().replace(" ", "_").replace("-", "_")
        tags = COMMON_XBRL_TAGS.get(common_key, [])

        if not tags:
            logger.warning("No known XBRL tags for common name '%s'", common_name)
            # Fall back to trying the name as a direct concept
            return await self.get_facts(
                cik, common_name,
                form_types=form_types,
                fiscal_periods=fiscal_periods,
            )

        for tag in tags:
            facts = await self.get_facts(
                cik, tag,
                form_types=form_types,
                fiscal_periods=fiscal_periods,
            )
            if facts:
                logger.info(
                    "Matched common name '%s' to XBRL tag '%s' for CIK %s (%d facts)",
                    common_name, tag, cik, len(facts),
                )
                return facts

        logger.warning(
            "No XBRL facts found for common name '%s' (tried tags: %s) for CIK %s",
            common_name, tags, cik,
        )
        return []

    async def get_annual_metric(
        self,
        cik: str,
        concept_or_common_name: str,
        *,
        latest_n: int = 3,
    ) -> list[XBRLFact]:
        """Convenience: get the N most recent annual (10-K) values for a metric.

        Handles several real-world complexities:
        1. Companies switch XBRL tags over time (e.g., Apple switched from
           "Revenues" to "RevenueFromContractWithCustomerExcludingAssessedTax"
           after FY2018). We try ALL known tags and merge results.
        2. A single 10-K filing reports data for multiple periods (the current
           year plus prior-year comparatives). All entries share the same
           `fy` value but have different `period_end` dates. We deduplicate
           by `period_end` and prefer the entry where this period was the
           primary reporting period (not a comparative).
        3. XBRL frame field distinguishes full-year (CY2023) from quarterly
           (CY2023Q3) sub-period breakdowns. We filter to full-year only.
        """
        import re

        all_facts: list[XBRLFact] = []

        # Get the common name key
        common_key = concept_or_common_name.lower().replace(" ", "_").replace("-", "_")

        if common_key in COMMON_XBRL_TAGS:
            # Try ALL known tags for this common name and merge results.
            # This handles companies that switched tags over time.
            tags = COMMON_XBRL_TAGS[common_key]
            for tag in tags:
                facts = await self.get_facts(
                    cik, tag,
                    form_types=["10-K"],
                    fiscal_periods=["FY"],
                )
                all_facts.extend(facts)
        else:
            all_facts = await self.get_facts(
                cik, concept_or_common_name,
                form_types=["10-K"],
                fiscal_periods=["FY"],
            )

        if not all_facts:
            return []

        # Filter to full-year frames only.
        # Full-year duration frames look like "CY2023" (no Q suffix).
        # Quarterly breakdowns look like "CY2023Q3" or "CY2023Q3I".
        # Entries without a frame are kept (they may be the primary value).
        QUARTERLY_FRAME_RE = re.compile(r"CY\d{4}Q\d")
        filtered = [
            f for f in all_facts
            if f.frame is None or not QUARTERLY_FRAME_RE.search(f.frame)
        ]

        # Deduplicate by period_end date (the actual reporting period, not fy).
        # When multiple entries exist for the same period_end:
        # - Prefer entries with a full-year frame (e.g., CY2023)
        # - Among those, prefer where the fiscal_year matches the period
        #   (i.e., this was the primary filing, not a comparative restatement)
        seen_periods: dict[str, XBRLFact] = {}
        for fact in filtered:
            key = fact.period_end
            if key not in seen_periods:
                seen_periods[key] = fact
            else:
                existing = seen_periods[key]
                # Prefer entry with a frame value
                if fact.frame and not existing.frame:
                    seen_periods[key] = fact
                # Among entries with frames, prefer where it's the primary period
                elif fact.frame and existing.frame:
                    # The primary period entry typically has fy matching the period
                    fact_is_primary = str(fact.fiscal_year) in (fact.frame or "")
                    existing_is_primary = str(existing.fiscal_year) in (existing.frame or "")
                    if fact_is_primary and not existing_is_primary:
                        seen_periods[key] = fact

        # Sort by period_end descending (newest first), take latest N
        deduped = sorted(seen_periods.values(), key=lambda f: f.period_end, reverse=True)
        return deduped[:latest_n]

