"""
Filing Sleuth — Disk Cache

EDGAR data is static once filed — a 10-K from 2023 will never change.
This cache avoids redundant fetches, respects SEC's rate limits, and makes
development faster (no waiting for network on every test run).

Cache structure on disk:
    cache_data/
    ├── tickers/
    │   └── company_tickers.json          # Full ticker→CIK mapping
    ├── submissions/
    │   └── CIK0000320193.json            # Submission history per CIK
    ├── xbrl/
    │   └── CIK0000320193.json            # CompanyFacts per CIK
    ├── filings/
    │   └── 0000320193/
    │       └── 0000320193-23-000106/
    │           ├── index.json            # Filing index page
    │           └── primary.html          # Primary filing document
    └── search/
        └── <hash>.json                   # Full-text search results

All cache reads/writes are synchronous (file I/O) — this is intentional.
EDGAR responses are small enough that async file I/O adds complexity without
meaningful benefit. The cache is checked BEFORE making any network request.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DiskCache:
    """Simple JSON file cache keyed by hierarchical path segments.

    Usage:
        cache = DiskCache(base_dir=Path("cache_data"))
        cache.put("submissions", "CIK0000320193", data=response_dict)
        cached = cache.get("submissions", "CIK0000320193")
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, *segments: str, suffix: str = ".json") -> Path:
        """Build the cache file path from hierarchical key segments.

        Example: ("submissions", "CIK0000320193") → cache_data/submissions/CIK0000320193.json
        """
        if not segments:
            raise ValueError("At least one key segment required")

        # All segments except the last become directories; last becomes the filename
        path = self.base_dir
        for seg in segments[:-1]:
            path = path / seg
        path = path / f"{segments[-1]}{suffix}"
        return path

    def get(self, *segments: str, suffix: str = ".json") -> dict | list | None:
        """Read cached JSON data. Returns None on cache miss."""
        path = self._resolve_path(*segments, suffix=suffix)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug("Cache HIT: %s", path.relative_to(self.base_dir))
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Cache read error for %s: %s", path, e)
            return None

    def put(self, *segments: str, data: Any, suffix: str = ".json") -> Path:
        """Write data to cache. Creates parent directories as needed."""
        path = self._resolve_path(*segments, suffix=suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Cache WRITE: %s", path.relative_to(self.base_dir))
        except OSError as e:
            logger.warning("Cache write error for %s: %s", path, e)
        return path

    def get_text(self, *segments: str, suffix: str = ".html") -> str | None:
        """Read cached text (HTML) data. Returns None on cache miss."""
        path = self._resolve_path(*segments, suffix=suffix)
        if not path.exists():
            return None
        try:
            text = path.read_text(encoding="utf-8")
            logger.debug("Cache HIT (text): %s", path.relative_to(self.base_dir))
            return text
        except OSError as e:
            logger.warning("Cache read error for %s: %s", path, e)
            return None

    def put_text(self, *segments: str, data: str, suffix: str = ".html") -> Path:
        """Write text (HTML) data to cache."""
        path = self._resolve_path(*segments, suffix=suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(data, encoding="utf-8")
            logger.debug("Cache WRITE (text): %s", path.relative_to(self.base_dir))
        except OSError as e:
            logger.warning("Cache write error for %s: %s", path, e)
        return path

    def has(self, *segments: str, suffix: str = ".json") -> bool:
        """Check if a cache entry exists."""
        return self._resolve_path(*segments, suffix=suffix).exists()

    @staticmethod
    def hash_key(value: str) -> str:
        """Create a short hash for use as a cache key (e.g., for search queries)."""
        return hashlib.sha256(value.encode()).hexdigest()[:16]
