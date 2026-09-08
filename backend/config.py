"""
Filing Sleuth — Application Configuration

Loads settings from environment variables (.env file).
All SEC API access requires the User-Agent header — this is the #1 thing people
forget when first hitting EDGAR APIs. Requests without it get 403'd.
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


# Project root = parent of backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    # ── SEC EDGAR ──────────────────────────────────────────────────────────
    # Format: "Your Name your-email@example.com"
    sec_user_agent: str = Field(
        default="FilingSleuth research-agent contact@filingsleuth.dev",
        description="SEC requires a descriptive User-Agent. Format: 'Name email@example.com'",
    )
    sec_rate_limit: int = Field(
        default=8,
        description="Max requests/second to SEC APIs. SEC allows up to 10.",
    )

    # SEC API base URLs (these don't change, but centralizing them here)
    sec_data_base: str = "https://data.sec.gov"
    sec_efts_base: str = "https://efts.sec.gov/LATEST"
    sec_www_base: str = "https://www.sec.gov"
    sec_archives_base: str = "https://www.sec.gov/Archives/edgar/data"

    # ── LLM ────────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="", description="Anthropic API key for Claude")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4o"

    # ── Embeddings ─────────────────────────────────────────────────────────
    embedding_provider: str = Field(
        default="local",
        description="'local' for sentence-transformers (free), 'openai' for text-embedding-3-small",
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Model name for the chosen embedding provider",
    )

    # ── Cache ──────────────────────────────────────────────────────────────
    cache_dir: Path = Field(
        default=PROJECT_ROOT / "cache_data",
        description="Directory for cached SEC API responses",
    )

    # ── Logging ────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def tickers_cache_path(self) -> Path:
        return self.cache_dir / "tickers"

    @property
    def submissions_cache_path(self) -> Path:
        return self.cache_dir / "submissions"

    @property
    def xbrl_cache_path(self) -> Path:
        return self.cache_dir / "xbrl"

    @property
    def filings_cache_path(self) -> Path:
        return self.cache_dir / "filings"

    @property
    def search_cache_path(self) -> Path:
        return self.cache_dir / "search"

    @property
    def chroma_db_path(self) -> Path:
        return self.cache_dir / "chroma"



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings singleton."""
    return Settings()
