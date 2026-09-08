"""
Filing Sleuth — Phase 2 Verification Script

Tests section parser against real 10-K HTML from cache.
Run: python -m backend.verify_phase2
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from backend.cache.disk_cache import DiskCache
from backend.config import get_settings
from backend.parsing.section_parser import SectionParser
from backend.parsing.chunk_builder import ChunkBuilder, FilingMetadata
from backend.retrieval.sec_client import SECClient
from backend.retrieval.submissions import SubmissionsAPI
from backend.retrieval.filing_fetcher import FilingFetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


TEST_FILINGS = [
    {"ticker": "AAPL", "cik": "0000320193", "name": "Apple Inc."},
    {"ticker": "TSLA", "cik": "0001318605", "name": "Tesla, Inc."},
    {"ticker": "MSFT", "cik": "0000789019", "name": "MICROSOFT CORP"},
]

# Key sections we expect to find in a 10-K
EXPECTED_ITEMS = {"1", "1A", "7", "8"}


async def main():
    print("=" * 70)
    print("FILING SLEUTH — Phase 2 Verification")
    print("Testing section parser against real 10-K filings")
    print("=" * 70)

    parser = SectionParser()
    builder = ChunkBuilder()
    all_ok = True

    async with SECClient() as client:
        subs_api = SubmissionsAPI(client)
        fetcher = FilingFetcher(client)

        for company in TEST_FILINGS:
            print(f"\n{'─' * 70}")
            print(f"  {company['ticker']} ({company['name']})")
            print(f"{'─' * 70}")

            # Get the most recent 10-K
            result = await subs_api.get_filings(
                company["cik"], form_types=["10-K"], limit=1,
            )
            if not result.filings:
                print(f"  ✗ No 10-K filings found")
                all_ok = False
                continue

            filing = result.filings[0]
            print(f"  Filing: {filing.accession_number} (filed {filing.filing_date})")

            # Fetch the HTML
            html = await fetcher.fetch_filing(
                cik=company["cik"],
                accession_number=filing.accession_number,
                primary_document=filing.primary_document,
            )
            print(f"  HTML size: {len(html):,} chars")

            # Parse into sections
            parse_result = parser.parse(html)

            print(f"  Detection method: {parse_result.detection_method}")
            print(f"  Sections found: {len(parse_result.sections)}")
            print(f"  Items: {', '.join(parse_result.items_found)}")

            if parse_result.warnings:
                for w in parse_result.warnings:
                    print(f"  ⚠ {w}")

            # Check for expected items
            found_items = set(parse_result.items_found)
            missing = EXPECTED_ITEMS - found_items
            if missing:
                print(f"  ⚠ Missing expected items: {missing}")
            else:
                print(f"  ✓ All key items found (1, 1A, 7, 8)")

            # Show section details
            for section in parse_result.sections:
                print(f"    Item {section.item_number:>3}: {section.item_title[:50]:50} "
                      f"({section.word_count:>6,} words)")

            # Build chunks
            metadata = FilingMetadata(
                company=company["name"],
                cik=company["cik"],
                accession_number=filing.accession_number,
                form_type="10-K",
                filing_date=filing.filing_date,
                reporting_date=filing.reporting_date,
            )
            chunks = builder.build_chunks(parse_result.sections, metadata)
            print(f"\n  Total chunks: {len(chunks)}")

            # Show chunk stats for key sections
            for item in ["1A", "7", "8"]:
                item_chunks = [c for c in chunks if c.item_number == item]
                if item_chunks:
                    total_words = sum(c.word_count for c in item_chunks)
                    print(f"    Item {item}: {len(item_chunks)} chunks, "
                          f"{total_words:,} total words")

            # Spot-check: does Item 7 text mention "revenue" / "net sales" or "income"?
            item7_chunks = [c for c in chunks if c.item_number == "7"]
            if item7_chunks:
                item7_text = " ".join(c.text for c in item7_chunks).lower()
                has_revenue = "revenue" in item7_text or "net sales" in item7_text or "sales" in item7_text
                has_income = "income" in item7_text or "earnings" in item7_text
                print(f"\n  Item 7 content check:")
                print(f"    Contains 'revenue/net sales': {'✓' if has_revenue else '✗'}")
                print(f"    Contains 'income/earnings': {'✓' if has_income else '✗'}")
                if not has_revenue:
                    print(f"    ⚠ Item 7 (MD&A) should discuss revenue/sales")
                    all_ok = False


    print(f"\n{'=' * 70}")
    print("RESULT:", "✓ ALL PASS" if all_ok else "⚠ ISSUES FOUND (see above)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
