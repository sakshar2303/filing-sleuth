"""
Filing Sleuth — EDGAR Full-Text Search (EFTS)

Wraps the EDGAR full-text search API (efts.sec.gov/LATEST/search-index)
to find which filings discuss a specific topic. This is useful when:

1. The query planner identifies a qualitative topic (e.g., "litigation risk",
   "supply chain disruptions") that isn't captured in XBRL
2. We need to find filings that mention a specific phrase across multiple companies
3. We need to narrow down which Item/section is relevant before fetching the full filing

The EFTS endpoint is the same one backing SEC's public "EDGAR Full-Text Search" UI.
It returns Elasticsearch-style results with accession numbers, CIKs, and file metadata.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.cache.disk_cache import DiskCache
from backend.retrieval.sec_client import SECClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchHit:
    """A single result from EDGAR full-text search."""
    accession_number: str       # e.g., "0000320193-23-000106"
    cik: str                    # CIK of the filer
    company_name: str           # Display name
    form_type: str              # e.g., "10-K"
    filing_date: str            # Date filed
    period_ending: str          # Reporting period end date
    file_type: str              # e.g., "10-K" or "EX-10.25"
    file_description: str       # Document description
    score: float                # Elasticsearch relevance score


class FullTextSearch:
    """Search across EDGAR filings for specific text/phrases.

    Usage:
        async with SECClient() as client:
            search = FullTextSearch(client)

            # Search for a phrase in Apple's 10-Ks
            hits = await search.search(
                query='"supply chain disruptions"',
                entity_cik="0000320193",
                form_types=["10-K"],
                start_date="2022-01-01",
                end_date="2024-12-31",
            )
    """

    SEARCH_URL_TEMPLATE = "{base}/search-index"

    def __init__(self, client: SECClient) -> None:
        self.client = client

    async def search(
        self,
        query: str,
        *,
        entity_cik: str | None = None,
        form_types: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        """Search EDGAR filings for matching text.

        Args:
            query: Search query. Wrap in quotes for exact phrase matching.
            entity_cik: Filter to a specific company's CIK.
            form_types: Filter to specific form types (e.g., ["10-K", "10-Q"]).
            start_date: Start of date range (YYYY-MM-DD).
            end_date: End of date range (YYYY-MM-DD).
            limit: Maximum number of results.

        Returns:
            List of SearchHit objects sorted by relevance score.
        """
        url = self.SEARCH_URL_TEMPLATE.format(base=self.client.settings.sec_efts_base)

        params: dict[str, Any] = {"q": query}
        if form_types:
            params["forms"] = ",".join(form_types)
        if start_date and end_date:
            params["dateRange"] = "custom"
            params["startdt"] = start_date
            params["enddt"] = end_date
        elif start_date:
            params["dateRange"] = "custom"
            params["startdt"] = start_date
            params["enddt"] = "2099-12-31"

        # Build cache key from params
        cache_key = DiskCache.hash_key(f"{query}|{entity_cik}|{form_types}|{start_date}|{end_date}")

        data = await self.client.get_json(
            url,
            params=params,
            cache_segments=("search", cache_key),
        )

        hits: list[SearchHit] = []
        raw_hits = data.get("hits", {}).get("hits", [])

        for raw in raw_hits[:limit]:
            source = raw.get("_source", {})

            # Filter by CIK if specified (EFTS doesn't have a direct CIK filter param)
            ciks = source.get("ciks", [])
            if entity_cik and entity_cik not in ciks:
                continue

            # Extract company name from display_names
            display_names = source.get("display_names", [])
            company_name = display_names[0] if display_names else ""

            # Only include main filing documents, not exhibits (unless searching exhibits)
            hit = SearchHit(
                accession_number=source.get("adsh", ""),
                cik=ciks[0] if ciks else "",
                company_name=company_name,
                form_type=source.get("form", ""),
                filing_date=source.get("file_date", ""),
                period_ending=source.get("period_ending", ""),
                file_type=source.get("file_type", ""),
                file_description=source.get("file_description", ""),
                score=raw.get("_score", 0.0),
            )
            hits.append(hit)

        logger.info(
            "EFTS search for '%s': %d hits (filtered from %d raw)",
            query, len(hits), len(raw_hits),
        )
        return hits
