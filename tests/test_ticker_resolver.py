"""
Filing Sleuth — Unit Tests for Ticker Resolver

Tests ticker resolution logic using mocked SEC API responses.
"""

import pytest
from unittest.mock import AsyncMock, patch

from backend.retrieval.ticker_resolver import TickerResolver, CompanyInfo
from backend.retrieval.sec_client import SECClient


# Mock ticker data matching SEC's actual format
MOCK_TICKERS = {
    "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": "789019", "ticker": "MSFT", "title": "MICROSOFT CORP"},
    "2": {"cik_str": "1318605", "ticker": "TSLA", "title": "Tesla, Inc."},
    "3": {"cik_str": "1652044", "ticker": "GOOGL", "title": "Alphabet Inc."},
}


class TestTickerResolver:
    @pytest.fixture
    async def resolver(self):
        """Create a resolver with mocked SEC client."""
        client = AsyncMock(spec=SECClient)
        client.get_json = AsyncMock(return_value=MOCK_TICKERS)
        return TickerResolver(client)

    @pytest.mark.asyncio
    async def test_resolve_by_ticker(self, resolver):
        result = await resolver.resolve("AAPL")
        assert result is not None
        assert result.cik == "0000320193"
        assert result.ticker == "AAPL"
        assert result.name == "Apple Inc."

    @pytest.mark.asyncio
    async def test_resolve_case_insensitive(self, resolver):
        result = await resolver.resolve("aapl")
        assert result is not None
        assert result.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_resolve_by_cik(self, resolver):
        result = await resolver.resolve("320193")
        assert result is not None
        assert result.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_resolve_by_name_substring(self, resolver):
        result = await resolver.resolve("Microsoft")
        assert result is not None
        assert result.ticker == "MSFT"

    @pytest.mark.asyncio
    async def test_resolve_not_found(self, resolver):
        result = await resolver.resolve("NONEXISTENT_COMPANY_XYZ")
        assert result is None

    @pytest.mark.asyncio
    async def test_cik_zero_padding(self, resolver):
        result = await resolver.resolve("AAPL")
        assert result is not None
        assert result.cik == "0000320193"  # 10-digit zero-padded
        assert result.cik_raw == 320193

    @pytest.mark.asyncio
    async def test_resolve_many(self, resolver):
        results = await resolver.resolve_many(["AAPL", "MSFT", "FAKE"])
        assert results["AAPL"] is not None
        assert results["MSFT"] is not None
        assert results["FAKE"] is None
