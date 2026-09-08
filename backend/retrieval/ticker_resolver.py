"""
Filing Sleuth — Ticker → CIK Resolution

Resolves stock tickers (AAPL, MSFT, TSLA) to SEC Central Index Keys (CIKs).
Uses SEC's company_tickers.json, which maps every registered entity to its
ticker and CIK. The file is cached locally (~1.5MB, updated infrequently).

The CIK is the primary key for all subsequent SEC API calls:
  - Submissions: data.sec.gov/submissions/CIK{cik10}.json
  - XBRL: data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json
  - Filing archives: sec.gov/Archives/edgar/data/{cik}/

CIKs are zero-padded to 10 digits for API URLs (e.g., "320193" → "0000320193").
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.retrieval.sec_client import SECClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompanyInfo:
    """Resolved company information from SEC ticker data."""
    cik: str          # 10-digit zero-padded CIK (e.g., "0000320193")
    cik_raw: int      # Raw CIK integer (e.g., 320193)
    ticker: str       # Stock ticker (e.g., "AAPL")
    name: str         # Company name (e.g., "Apple Inc.")


class TickerResolver:
    """Resolves stock tickers to SEC CIK numbers.

    Usage:
        async with SECClient() as client:
            resolver = TickerResolver(client)
            company = await resolver.resolve("AAPL")
            # CompanyInfo(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    """

    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

    def __init__(self, client: SECClient) -> None:
        self.client = client
        # In-memory indices built from the ticker file
        self._by_ticker: dict[str, CompanyInfo] = {}
        self._by_cik: dict[int, CompanyInfo] = {}
        self._by_name: dict[str, CompanyInfo] = {}
        self._loaded = False

    async def _load(self) -> None:
        """Download and index the SEC company tickers file."""
        if self._loaded:
            return

        logger.info("Loading SEC company tickers...")
        data = await self.client.get_json(
            self.TICKERS_URL,
            cache_segments=("tickers", "company_tickers"),
        )

        # The file is a dict of {"0": {"cik_str": ..., "ticker": ..., "title": ...}, ...}
        for _idx, entry in data.items():
            cik_raw = int(entry["cik_str"])
            info = CompanyInfo(
                cik=str(cik_raw).zfill(10),
                cik_raw=cik_raw,
                ticker=entry["ticker"].upper(),
                name=entry["title"],
            )
            self._by_ticker[info.ticker] = info
            self._by_cik[cik_raw] = info
            # Index by normalized name for fuzzy lookup
            self._by_name[info.name.upper()] = info

        self._loaded = True
        logger.info("Loaded %d company tickers", len(self._by_ticker))

    async def resolve(self, query: str) -> CompanyInfo | None:
        """Resolve a ticker symbol or company name to CompanyInfo.

        Tries in order:
        1. Exact ticker match (case-insensitive)
        2. Exact CIK match (if query is numeric)
        3. Exact company name match (case-insensitive)
        4. Substring match on company name (returns first match)

        Returns None if no match found.
        """
        await self._load()

        query_upper = query.strip().upper()

        # 1. Exact ticker match
        if query_upper in self._by_ticker:
            result = self._by_ticker[query_upper]
            logger.info("Resolved ticker '%s' → CIK %s (%s)", query, result.cik, result.name)
            return result

        # 2. CIK match (if query is numeric)
        if query.strip().isdigit():
            cik_int = int(query.strip())
            if cik_int in self._by_cik:
                result = self._by_cik[cik_int]
                logger.info("Resolved CIK %d → %s (%s)", cik_int, result.ticker, result.name)
                return result

        # 3. Exact company name match
        if query_upper in self._by_name:
            result = self._by_name[query_upper]
            logger.info("Resolved name '%s' → CIK %s (%s)", query, result.cik, result.ticker)
            return result

        # 4. Substring match on company name (first match)
        for name, info in self._by_name.items():
            if query_upper in name:
                logger.info(
                    "Resolved name substring '%s' → CIK %s (%s)",
                    query, info.cik, info.name,
                )
                return info

        logger.warning("Could not resolve '%s' to any SEC registrant", query)
        return None

    async def resolve_many(self, queries: list[str]) -> dict[str, CompanyInfo | None]:
        """Resolve multiple tickers/names. Returns a dict of query → CompanyInfo."""
        await self._load()
        return {q: await self.resolve(q) for q in queries}

    async def search_companies(self, query: str = "", limit: int = 10) -> list[dict[str, str]]:
        """Search companies by ticker prefix or name substring for autocomplete."""
        await self._load()
        q = query.strip().upper()
        if not q:
            # Return popular top companies by default
            default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "JPM", "V", "WMT"]
            res = []
            for t in default_tickers:
                if t in self._by_ticker:
                    info = self._by_ticker[t]
                    res.append({"ticker": info.ticker, "name": info.name, "cik": info.cik})
            return res

        matches: list[dict[str, str]] = []
        # Priority 1: Exact or prefix ticker match
        for ticker, info in self._by_ticker.items():
            if ticker.startswith(q):
                matches.append({"ticker": info.ticker, "name": info.name, "cik": info.cik})
                if len(matches) >= limit:
                    return matches

        # Priority 2: Substring in company name
        for name, info in self._by_name.items():
            if q in name and not any(m["ticker"] == info.ticker for m in matches):
                matches.append({"ticker": info.ticker, "name": info.name, "cik": info.cik})
                if len(matches) >= limit:
                    return matches

        return matches

