"""
Filing Sleuth — Filing Document Fetcher

Fetches the actual HTML content of SEC filings (10-K, 10-Q) by accession number.

The process:
1. Build the filing index URL from CIK + accession number
2. Fetch the index page to find the primary document filename
3. Fetch the primary document HTML

The filing archive URL structure is:
  https://www.sec.gov/Archives/edgar/data/{cik}/{accession-with-dashes}/{filename}

Where accession-with-dashes converts "0000320193-23-000106" to "000032019323000106"
(removing dashes for the directory path, but keeping them for the filename).

Actually, SEC uses the format with dashes in the directory path too:
  https://www.sec.gov/Archives/edgar/data/{cik_raw}/{accn_dashes}/

Example:
  https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/
"""

from __future__ import annotations

import logging
import re

from backend.retrieval.sec_client import SECClient

logger = logging.getLogger(__name__)


class FilingFetcher:
    """Fetch filing documents from SEC EDGAR archives.

    Usage:
        async with SECClient() as client:
            fetcher = FilingFetcher(client)

            # If you already know the primary document filename (from submissions API):
            html = await fetcher.fetch_filing(
                cik="0000320193",
                accession_number="0000320193-23-000106",
                primary_document="aapl-20230930.htm",
            )

            # If you don't know the filename, fetch the index first:
            index = await fetcher.fetch_filing_index("0000320193", "0000320193-23-000106")
            primary_doc = fetcher.find_primary_document(index)
    """

    def __init__(self, client: SECClient) -> None:
        self.client = client

    def _build_filing_base_url(self, cik: str, accession_number: str) -> str:
        """Build the base URL for a filing's archive directory.

        SEC uses the raw CIK (no leading zeros) and the accession number
        with dashes removed for the directory path.
        """
        cik_raw = str(int(cik))  # Remove leading zeros: "0000320193" → "320193"
        accn_no_dashes = accession_number.replace("-", "")
        return (
            f"{self.client.settings.sec_archives_base}"
            f"/{cik_raw}/{accn_no_dashes}"
        )

    async def fetch_filing_index(
        self,
        cik: str,
        accession_number: str,
    ) -> str:
        """Fetch the filing index page HTML.

        The index page lists all documents in the filing package.
        Returns the raw HTML string.
        """
        base_url = self._build_filing_base_url(cik, accession_number)
        index_url = f"{base_url}/index.json"

        try:
            # Try JSON index first (cleaner to parse)
            data = await self.client.get_json(
                index_url,
                cache_segments=("filings", cik, accession_number, "index"),
            )
            return data
        except Exception:
            # Fall back to HTML index
            html_url = f"{base_url}/"
            return await self.client.get_text(
                html_url,
                cache_segments=("filings", cik, accession_number, "index_html"),
                cache_suffix=".html",
            )

    def find_primary_document_from_index(self, index_data: dict) -> str | None:
        """Extract the primary document filename from a JSON filing index.

        The primary document is typically the 10-K or 10-Q HTML file —
        the largest .htm file, or the one with sequence "1".
        """
        if not isinstance(index_data, dict):
            return None

        directory = index_data.get("directory", {})
        items = directory.get("item", [])

        # Look for the primary document: sequence 1, or the main .htm file
        htm_files = []
        for item in items:
            name = item.get("name", "")
            if name.lower().endswith((".htm", ".html")) and not name.startswith("R"):
                # Skip the R*.htm files (XBRL rendering files)
                size = item.get("size", "0")
                try:
                    size_int = int(str(size).replace(",", ""))
                except ValueError:
                    size_int = 0
                htm_files.append((name, size_int))

        if not htm_files:
            return None

        # The primary document is usually the largest .htm file
        htm_files.sort(key=lambda x: x[1], reverse=True)
        primary = htm_files[0][0]
        logger.debug("Identified primary document: %s", primary)
        return primary

    async def fetch_filing(
        self,
        cik: str,
        accession_number: str,
        primary_document: str | None = None,
    ) -> str:
        """Fetch the full HTML text of a filing's primary document.

        Args:
            cik: 10-digit zero-padded CIK.
            accession_number: Filing accession number (e.g., "0000320193-23-000106").
            primary_document: Filename of the primary document (e.g., "aapl-20230930.htm").
                              If None, will be auto-detected from the filing index.

        Returns:
            Raw HTML string of the filing document.

        Raises:
            ValueError: If primary document cannot be determined.
        """
        # Auto-detect primary document if not provided
        if primary_document is None:
            index = await self.fetch_filing_index(cik, accession_number)
            if isinstance(index, dict):
                primary_document = self.find_primary_document_from_index(index)
            if primary_document is None:
                raise ValueError(
                    f"Could not determine primary document for "
                    f"CIK {cik}, accession {accession_number}"
                )

        base_url = self._build_filing_base_url(cik, accession_number)
        doc_url = f"{base_url}/{primary_document}"

        html = await self.client.get_text(
            doc_url,
            cache_segments=("filings", cik, accession_number, "primary"),
            cache_suffix=".html",
        )

        logger.info(
            "Fetched filing document: CIK %s, accession %s, doc %s (%d chars)",
            cik, accession_number, primary_document, len(html),
        )
        return html

    def build_edgar_url(self, cik: str, accession_number: str, document: str = "") -> str:
        """Build a public EDGAR URL for linking in citations.

        Returns a URL the user can click to view the filing on SEC.gov.
        """
        base_url = self._build_filing_base_url(cik, accession_number)
        if document:
            return f"{base_url}/{document}"
        return f"{base_url}/"
