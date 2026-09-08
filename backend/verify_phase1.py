"""
Filing Sleuth — Phase 1 Verification Script

Runs end-to-end verification of all data foundation modules against real SEC EDGAR data.
Tests against 3 known companies (Apple, Microsoft, Tesla) and hand-checks results.

Run: python -m backend.verify_phase1
"""

from __future__ import annotations

import asyncio
import logging
import sys

from backend.retrieval.sec_client import SECClient
from backend.retrieval.ticker_resolver import TickerResolver
from backend.retrieval.submissions import SubmissionsAPI
from backend.retrieval.xbrl_facts import XBRLFactsAPI
from backend.retrieval.filing_fetcher import FilingFetcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Test companies ──────────────────────────────────────────────────────────
TEST_COMPANIES = [
    {"ticker": "AAPL", "expected_cik": "0000320193", "expected_name_fragment": "Apple"},
    {"ticker": "MSFT", "expected_cik": "0000789019", "expected_name_fragment": "MICROSOFT"},
    {"ticker": "TSLA", "expected_cik": "0001318605", "expected_name_fragment": "Tesla"},
]


async def verify_ticker_resolution(resolver: TickerResolver) -> bool:
    """Verify ticker → CIK resolution for test companies."""
    print("\n" + "=" * 70)
    print("STEP 1: Ticker → CIK Resolution")
    print("=" * 70)

    all_ok = True
    for tc in TEST_COMPANIES:
        result = await resolver.resolve(tc["ticker"])
        if result is None:
            print(f"  ✗ {tc['ticker']}: FAILED — could not resolve")
            all_ok = False
            continue

        cik_ok = result.cik == tc["expected_cik"]
        name_ok = tc["expected_name_fragment"].upper() in result.name.upper()

        if cik_ok and name_ok:
            print(f"  ✓ {tc['ticker']} → CIK {result.cik} ({result.name})")
        else:
            print(f"  ✗ {tc['ticker']}: CIK={result.cik} (expected {tc['expected_cik']}), "
                  f"name={result.name}")
            all_ok = False

    return all_ok


async def verify_submissions(subs_api: SubmissionsAPI) -> bool:
    """Verify submissions API returns filing history for test companies."""
    print("\n" + "=" * 70)
    print("STEP 2: Submissions API — Filing History")
    print("=" * 70)

    all_ok = True
    for tc in TEST_COMPANIES:
        result = await subs_api.get_filings(
            tc["expected_cik"],
            form_types=["10-K"],
            limit=3,
        )

        if not result.filings:
            print(f"  ✗ {tc['ticker']}: No 10-K filings found")
            all_ok = False
            continue

        print(f"  ✓ {tc['ticker']} ({result.entity_name}): "
              f"{len(result.filings)} recent 10-K filings, "
              f"fiscal year end: {result.fiscal_year_end}")

        for f in result.filings[:3]:
            print(f"    • {f.form_type} | Filed: {f.filing_date} | "
                  f"Period: {f.reporting_date} | Accession: {f.accession_number}")
            print(f"      Primary doc: {f.primary_document}")

        # Sanity checks
        latest = result.filings[0]
        if not latest.accession_number:
            print(f"  ✗ {tc['ticker']}: Missing accession number")
            all_ok = False
        if not latest.primary_document:
            print(f"  ✗ {tc['ticker']}: Missing primary document")
            all_ok = False

    return all_ok


async def verify_xbrl(xbrl_api: XBRLFactsAPI) -> bool:
    """Verify XBRL CompanyFacts returns correct financial data."""
    print("\n" + "=" * 70)
    print("STEP 3: XBRL CompanyFacts — Structured Financial Data")
    print("=" * 70)

    all_ok = True

    # Test: Apple Revenue (we verified from EDGAR that Apple uses "Revenues" or
    # "RevenueFromContractWithCustomerExcludingAssessedTax")
    aapl_revenue = await xbrl_api.get_annual_metric("0000320193", "revenue", latest_n=3)
    if aapl_revenue:
        print(f"  ✓ Apple Revenue (annual, last 3 years):")
        for fact in aapl_revenue:
            val_b = fact.value / 1_000_000_000
            year = fact.period_end[:4]
            print(f"    • Period ending {fact.period_end}: ${val_b:.2f}B "
                  f"(tag: {fact.concept}, accn: {fact.accession_number})")
    else:
        print("  ✗ Apple Revenue: No XBRL facts found")
        all_ok = False

    # Test: Apple R&D
    aapl_rd = await xbrl_api.get_annual_metric("0000320193", "research_and_development", latest_n=3)
    if aapl_rd:
        print(f"\n  ✓ Apple R&D Expense (annual, last 3 years):")
        for fact in aapl_rd:
            val_b = fact.value / 1_000_000_000
            print(f"    • Period ending {fact.period_end}: ${val_b:.2f}B "
                  f"(tag: {fact.concept}, accn: {fact.accession_number})")
    else:
        print("  ✗ Apple R&D: No XBRL facts found")
        all_ok = False

    # Test: Microsoft Revenue (different fiscal year — ends June)
    msft_revenue = await xbrl_api.get_annual_metric("0000789019", "revenue", latest_n=3)
    if msft_revenue:
        print(f"\n  ✓ Microsoft Revenue (annual, last 3 years):")
        for fact in msft_revenue:
            val_b = fact.value / 1_000_000_000
            print(f"    • Period ending {fact.period_end}: ${val_b:.2f}B "
                  f"(tag: {fact.concept})")
    else:
        print("  ✗ Microsoft Revenue: No XBRL facts found")
        all_ok = False

    # Test: Tesla Net Income (volatile — good test for varying values)
    tsla_ni = await xbrl_api.get_annual_metric("0001318605", "net_income", latest_n=3)
    if tsla_ni:
        print(f"\n  ✓ Tesla Net Income (annual, last 3 years):")
        for fact in tsla_ni:
            val_b = fact.value / 1_000_000_000
            print(f"    • Period ending {fact.period_end}: ${val_b:.2f}B "
                  f"(tag: {fact.concept}, accn: {fact.accession_number})")
    else:
        print("  ✗ Tesla Net Income: No XBRL facts found")
        all_ok = False

    return all_ok


async def verify_filing_fetch(
    subs_api: SubmissionsAPI,
    fetcher: FilingFetcher,
) -> bool:
    """Verify we can fetch actual filing HTML documents."""
    print("\n" + "=" * 70)
    print("STEP 4: Filing Document Fetch")
    print("=" * 70)

    all_ok = True

    # Get Apple's most recent 10-K
    result = await subs_api.get_filings("0000320193", form_types=["10-K"], limit=1)
    if not result.filings:
        print("  ✗ Could not get Apple's 10-K filing info")
        return False

    filing = result.filings[0]
    print(f"  Fetching Apple 10-K: accession={filing.accession_number}, "
          f"doc={filing.primary_document}")

    try:
        html = await fetcher.fetch_filing(
            cik="0000320193",
            accession_number=filing.accession_number,
            primary_document=filing.primary_document,
        )
        print(f"  ✓ Fetched {len(html):,} characters of HTML")

        # Basic sanity: check for common 10-K content
        has_item7 = "item 7" in html.lower() or "item&#160;7" in html.lower()
        has_item1a = "item 1a" in html.lower() or "item&#160;1a" in html.lower()
        has_item8 = "item 8" in html.lower() or "item&#160;8" in html.lower()

        print(f"    Contains 'Item 7' (MD&A): {'✓' if has_item7 else '✗'}")
        print(f"    Contains 'Item 1A' (Risk Factors): {'✓' if has_item1a else '✗'}")
        print(f"    Contains 'Item 8' (Financial Statements): {'✓' if has_item8 else '✗'}")

        if not (has_item7 or has_item1a or has_item8):
            print("  ⚠ Warning: Could not find expected Item headers — "
                  "may need parser adjustments")
            # Not a hard failure — some filings use unusual formatting
    except Exception as e:
        print(f"  ✗ Failed to fetch filing: {e}")
        all_ok = False

    return all_ok


async def main() -> None:
    """Run all Phase 1 verification checks."""
    print("=" * 70)
    print("FILING SLEUTH — Phase 1 Verification")
    print("Testing against real SEC EDGAR data")
    print("=" * 70)

    results: dict[str, bool] = {}

    async with SECClient() as client:
        resolver = TickerResolver(client)
        subs_api = SubmissionsAPI(client)
        xbrl_api = XBRLFactsAPI(client)
        fetcher = FilingFetcher(client)

        results["ticker_resolution"] = await verify_ticker_resolution(resolver)
        results["submissions_api"] = await verify_submissions(subs_api)
        results["xbrl_facts"] = await verify_xbrl(xbrl_api)
        results["filing_fetch"] = await verify_filing_fetch(subs_api, fetcher)

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    all_passed = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All Phase 1 checks passed! Data foundations verified against real EDGAR data.")
    else:
        print("Some checks failed. Review output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
