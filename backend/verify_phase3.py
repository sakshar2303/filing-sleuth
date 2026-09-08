"""
Filing Sleuth — Phase 3 Verification Script

Indexes real 10-K filings for Apple, Tesla, and Microsoft, and verifies
retrieval accuracy across vector, BM25, and hybrid search against hand-verified
financial queries.
Run: python -m backend.verify_phase3
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from backend.cache.disk_cache import DiskCache
from backend.config import get_settings
from backend.indexing.bm25_index import BM25Index
from backend.indexing.hybrid_search import HybridSearchEngine
from backend.indexing.vector_store import VectorStore
from backend.parsing.chunk_builder import ChunkBuilder, FilingMetadata
from backend.parsing.section_parser import SectionParser
from backend.retrieval.filing_fetcher import FilingFetcher
from backend.retrieval.sec_client import SECClient
from backend.retrieval.submissions import SubmissionsAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

COMPANIES = [
    {"ticker": "AAPL", "cik": "0000320193", "name": "Apple Inc."},
    {"ticker": "TSLA", "cik": "0001318605", "name": "Tesla, Inc."},
    {"ticker": "MSFT", "cik": "0000789019", "name": "MICROSOFT CORP"},
]

# Queries to evaluate retrieval precision
TEST_QUERIES = [
    {
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "cik": "0000320193",
        "query": "Services net sales and App Store growth",
        "expected_items": ["7", "1", "1A", "3"],
        "must_contain_any": ["services", "app store", "net sales"],
    },
    {
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "cik": "0000320193",
        "query": "Net sales by product category iPhone Services Wearables",
        "item_filter": "7",
        "expected_items": ["7"],
        "must_contain_any": ["net sales", "iphone", "services"],
    },
    {
        "company": "Tesla, Inc.",
        "ticker": "TSLA",
        "cik": "0001318605",
        "query": "Full Self-Driving FSD autonomous vehicle safety risks",
        "expected_items": ["1A", "1"],
        "must_contain_any": ["full self-driving", "fsd", "autonomous", "autopilot"],
    },
    {
        "company": "MICROSOFT CORP",
        "ticker": "MSFT",
        "cik": "0000789019",
        "query": "Azure cloud services revenue growth and Intelligent Cloud",
        "expected_items": ["7", "1"],
        "must_contain_any": ["azure", "intelligent cloud", "cloud"],
    },
    {
        "company": "MICROSOFT CORP",
        "ticker": "MSFT",
        "cik": "0000789019",
        "query": "Cybersecurity risk management strategy and governance",
        "expected_items": ["1C", "1A"],
        "must_contain_any": ["cybersecurity", "cyber", "threat"],
    },
]



async def main():
    print("=" * 70)
    print("FILING SLEUTH — Phase 3 Verification")
    print("Testing Hybrid Retrieval (Vector + BM25) on real 10-K filings")
    print("=" * 70)

    parser = SectionParser()
    builder = ChunkBuilder()
    vector_store = VectorStore()
    bm25_index = BM25Index()
    engine = HybridSearchEngine(vector_store=vector_store, bm25_index=bm25_index)

    all_chunks = []

    async with SECClient() as client:
        subs_api = SubmissionsAPI(client)
        fetcher = FilingFetcher(client)

        for company in COMPANIES:
            print(f"\nProcessing {company['ticker']} ({company['name']})...")
            result = await subs_api.get_filings(company["cik"], form_types=["10-K"], limit=1)
            if not result.filings:
                print(f"  ✗ No 10-K found for {company['ticker']}")
                continue

            filing = result.filings[0]
            html = await fetcher.fetch_filing(
                cik=company["cik"],
                accession_number=filing.accession_number,
                primary_document=filing.primary_document,
            )

            parse_result = parser.parse(html)
            meta = FilingMetadata(
                company=company["name"],
                cik=company["cik"],
                accession_number=filing.accession_number,
                form_type="10-K",
                filing_date=filing.filing_date,
                reporting_date=filing.reporting_date,
            )
            chunks = builder.build_chunks(parse_result.sections, meta)
            all_chunks.extend(chunks)
            print(f"  Built {len(chunks)} chunks from {len(parse_result.sections)} sections")

    print(f"\nIndexing {len(all_chunks)} chunks into VectorStore & BM25...")
    counts = engine.index_filing_chunks(all_chunks)
    print(f"  VectorStore chunks: {counts['vector']}, BM25 chunks: {counts['bm25']}")

    print("\n" + "─" * 70)
    print("EVALUATING TEST QUERIES")
    print("─" * 70)

    all_pass = True

    for test in TEST_QUERIES:
        ticker = test["ticker"]
        query = test["query"]
        cik = test["cik"]
        expected_items = test["expected_items"]
        must_contain = test["must_contain_any"]

        print(f"\nQuery [{ticker}]: \"{query}\"")

        item_filter = test.get("item_filter")
        results = engine.search(query, n_results=3, cik=cik, item_number=item_filter)
        if not results:

            print("  ✗ No results returned!")
            all_pass = False
            continue

        top_hit = results[0]
        hit_item = top_hit.item_number
        hit_text_lower = top_hit.text.lower()

        item_match = hit_item in expected_items
        content_match = any(term in hit_text_lower for term in must_contain)

        print(f"  Top Hit: Item {top_hit.item_number} ({top_hit.item_title})")
        print(f"    RRF Score: {top_hit.rrf_score:.5f} | Vec Rank: {top_hit.vector_rank} | BM25 Rank: {top_hit.bm25_rank}")
        print(f"    Item in expected {expected_items}: {'✓' if item_match else '✗'}")
        print(f"    Contains key terminology {must_contain}: {'✓' if content_match else '✗'}")
        print(f"    Preview: {top_hit.text[:180].strip()}...")

        if not (item_match and content_match):
            print("  ⚠ Top hit did not meet verification criteria")
            all_pass = False
        else:
            print("  ✓ PASS")

    print("\n" + "=" * 70)
    print("RESULT:", "✓ ALL RETRIEVAL TESTS PASS" if all_pass else "⚠ SOME TESTS FAILED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
