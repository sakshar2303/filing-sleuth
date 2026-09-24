"""
Filing Sleuth — SEC HTTP Client

Central HTTP client for all SEC EDGAR API access. Handles:
- Required User-Agent header (SEC blocks requests without it)
- Rate limiting (≤10 req/s, we default to 8 for safety margin)
- Exponential backoff on 429/5xx errors
- Response caching via DiskCache (EDGAR data is immutable once filed)
- Connection pooling via httpx.AsyncClient

IMPORTANT: Every request to *.sec.gov MUST include the User-Agent header.
This is not optional — it's the #1 cause of 403 errors when hitting EDGAR.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from backend.config import Settings, get_settings
from backend.cache.disk_cache import DiskCache

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket rate limiter for SEC's 10 req/s limit.

    We use a simple sliding window: track timestamps of recent requests
    and sleep if we'd exceed the limit. This is simpler and more
    predictable than asyncio-throttle for our use case.
    """

    def __init__(self, max_per_second: int = 8) -> None:
        self.max_per_second = max_per_second
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            # Discard timestamps older than 1 second
            self._timestamps = [t for t in self._timestamps if now - t < 1.0]

            if len(self._timestamps) >= self.max_per_second:
                # Sleep until the oldest timestamp is >1s ago
                sleep_time = 1.0 - (now - self._timestamps[0])
                if sleep_time > 0:
                    logger.debug("Rate limit: sleeping %.3fs", sleep_time)
                    await asyncio.sleep(sleep_time)

            self._timestamps.append(time.monotonic())


class SECClient:
    """Async HTTP client for SEC EDGAR APIs.

    Usage:
        async with SECClient() as client:
            data = await client.get_json("https://data.sec.gov/...")
            html = await client.get_text("https://www.sec.gov/Archives/...")
    """

    # Retry config
    MAX_RETRIES = 3
    BACKOFF_BASE = 2.0  # seconds
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.cache = DiskCache(self.settings.cache_dir)
        self._rate_limiter = RateLimiter(self.settings.sec_rate_limit)
        self._client: httpx.AsyncClient | None = None

    def _create_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "User-Agent": self.settings.sec_user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            http2=True,
        )

    async def __aenter__(self) -> SECClient:
        if self._client is None:
            self._client = self._create_client()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = self._create_client()
        return self._client

    async def _request(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a rate-limited, retrying HTTP GET request."""
        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            await self._rate_limiter.acquire()

            try:
                response = await self.client.get(url, params=params)

                if response.status_code == 200:
                    return response

                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    wait = self.BACKOFF_BASE ** attempt
                    logger.warning(
                        "SEC API %d for %s (attempt %d/%d), retrying in %.1fs",
                        response.status_code,
                        url,
                        attempt + 1,
                        self.MAX_RETRIES,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                # Non-retryable error (403, 404, etc.)
                response.raise_for_status()

            except httpx.TimeoutException as e:
                wait = self.BACKOFF_BASE ** attempt
                logger.warning(
                    "Timeout for %s (attempt %d/%d), retrying in %.1fs",
                    url,
                    attempt + 1,
                    self.MAX_RETRIES,
                    wait,
                )
                last_error = e
                await asyncio.sleep(wait)
            except httpx.HTTPStatusError:
                raise  # Non-retryable HTTP errors propagate immediately

        raise httpx.ConnectError(
            f"Failed after {self.MAX_RETRIES} attempts for {url}"
        ) from last_error

    async def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        cache_segments: tuple[str, ...] | None = None,
    ) -> dict | list:
        """Fetch JSON from a SEC API endpoint, with optional caching.

        Args:
            url: The API URL.
            params: Query parameters.
            cache_segments: If provided, cache the response at these path segments.
                Example: ("submissions", "CIK0000320193")
        """
        # Check cache first
        if cache_segments:
            cached = self.cache.get(*cache_segments)
            if cached is not None:
                return cached

        response = await self._request(url, params=params)
        data = response.json()

        # Write to cache
        if cache_segments:
            self.cache.put(*cache_segments, data=data)

        return data

    async def get_text(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        cache_segments: tuple[str, ...] | None = None,
        cache_suffix: str = ".html",
    ) -> str:
        """Fetch text/HTML from a SEC URL, with optional caching.

        Args:
            url: The URL to fetch.
            params: Query parameters.
            cache_segments: If provided, cache the response at these path segments.
            cache_suffix: File extension for cached text (default: .html).
        """
        # Check cache first
        if cache_segments:
            cached = self.cache.get_text(*cache_segments, suffix=cache_suffix)
            if cached is not None:
                return cached

        response = await self._request(url, params=params)
        text = response.text

        # Write to cache
        if cache_segments:
            self.cache.put_text(*cache_segments, data=text, suffix=cache_suffix)

        return text
