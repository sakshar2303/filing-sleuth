"""
Filing Sleuth — Unit Tests for Disk Cache

Tests the cache layer in isolation — no network calls.
"""

import json
import tempfile
from pathlib import Path

from backend.cache.disk_cache import DiskCache


class TestDiskCache:
    def setup_method(self):
        """Create a temporary cache directory for each test."""
        self._tmp = tempfile.mkdtemp()
        self.cache = DiskCache(Path(self._tmp))

    def test_put_and_get_json(self):
        data = {"ticker": "AAPL", "cik": 320193}
        self.cache.put("tickers", "test_entry", data=data)
        result = self.cache.get("tickers", "test_entry")
        assert result == data

    def test_get_miss(self):
        result = self.cache.get("nonexistent", "key")
        assert result is None

    def test_has(self):
        self.cache.put("submissions", "CIK0000320193", data={"filings": []})
        assert self.cache.has("submissions", "CIK0000320193")
        assert not self.cache.has("submissions", "CIK9999999999")

    def test_nested_segments(self):
        data = {"content": "test html"}
        self.cache.put("filings", "320193", "0000320193-23-000106", "index", data=data)
        result = self.cache.get("filings", "320193", "0000320193-23-000106", "index")
        assert result == data

    def test_put_and_get_text(self):
        html = "<html><body>Test filing content</body></html>"
        self.cache.put_text("filings", "320193", "primary", data=html)
        result = self.cache.get_text("filings", "320193", "primary")
        assert result == html

    def test_text_get_miss(self):
        result = self.cache.get_text("filings", "nonexistent", "doc")
        assert result is None

    def test_hash_key(self):
        h1 = DiskCache.hash_key("revenue apple 10-K")
        h2 = DiskCache.hash_key("revenue apple 10-K")
        h3 = DiskCache.hash_key("different query")
        assert h1 == h2  # Same input → same hash
        assert h1 != h3  # Different input → different hash
        assert len(h1) == 16  # Truncated to 16 chars

    def test_overwrite(self):
        self.cache.put("test", "key", data={"version": 1})
        self.cache.put("test", "key", data={"version": 2})
        result = self.cache.get("test", "key")
        assert result == {"version": 2}

    def test_corrupt_json_returns_none(self):
        """If a cached file has invalid JSON, return None rather than crashing."""
        path = self.cache._resolve_path("test", "corrupt")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json {{{", encoding="utf-8")
        result = self.cache.get("test", "corrupt")
        assert result is None
