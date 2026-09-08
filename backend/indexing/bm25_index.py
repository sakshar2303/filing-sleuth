"""
Filing Sleuth — BM25 Keyword Search Index

Provides fast, term-exact retrieval using Okapi BM25 (rank_bm25).
This complements dense vector search by catching exact names, ticker symbols,
financial statement line item captions, and regulation references (e.g. "ASC 606",
"Item 1A", "Qualcomm", "NVIDIA").
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from rank_bm25 import BM25Okapi

from backend.parsing.chunk_builder import SectionChunk

logger = logging.getLogger(__name__)

# Basic stopwords to avoid indexing trivial tokens
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves",
}

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")


def tokenize(text: str) -> list[str]:
    """Tokenize text for BM25: lowercase, strip punctuation, filter stopwords."""
    tokens = TOKEN_PATTERN.findall(text.lower())
    return [t for t in tokens if len(t) > 1 and t not in STOPWORDS]


@dataclass
class BM25SearchResult:
    """A scored search result from BM25 index."""
    chunk: SectionChunk
    score: float
    rank: int


class BM25Index:
    """In-memory BM25 index supporting incremental indexing and metadata filtering.

    Usage:
        index = BM25Index()
        index.index_chunks(chunks)
        results = index.search("antitrust DOJ lawsuit", n_results=5, item_number="1A")
    """

    def __init__(self) -> None:
        self.chunks: list[SectionChunk] = []
        self.corpus_tokens: list[list[str]] = []
        self._bm25: BM25Okapi | None = None
        self._indexed_ids: set[str] = set()

    def index_chunks(self, chunks: list[SectionChunk]) -> int:
        """Add new chunks to the index and re-fit BM25 model.

        Returns number of newly indexed chunks.
        """
        new_chunks = [c for c in chunks if c.chunk_id not in self._indexed_ids]
        if not new_chunks:
            return 0

        for chunk in new_chunks:
            # Combine item title + text for richer keyword matching
            full_text = f"Item {chunk.item_number} {chunk.item_title}\n{chunk.text}"
            tokens = tokenize(full_text)
            self.corpus_tokens.append(tokens)
            self.chunks.append(chunk)
            self._indexed_ids.add(chunk.chunk_id)

        # Fit or re-fit BM25
        self._bm25 = BM25Okapi(self.corpus_tokens)
        logger.info(
            "Indexed %d new chunks into BM25 (total chunks: %d)",
            len(new_chunks), len(self.chunks),
        )
        return len(new_chunks)

    def search(
        self,
        query: str,
        n_results: int = 10,
        *,
        cik: str | None = None,
        accession_number: str | None = None,
        item_number: str | None = None,
        item_numbers: list[str] | None = None,
        min_score: float | None = None,
    ) -> list[BM25SearchResult]:
        """Query the BM25 index with optional metadata pre-filtering.

        Args:
            query: Natural language query or keywords.
            n_results: Max number of results to return.
            cik: Optional CIK filter.
            accession_number: Optional accession number filter.
            item_number: Optional single Item number filter (e.g., "1A").
            item_numbers: Optional list of Item numbers to allow.
            min_score: Optional minimum BM25 score threshold.

        Returns:
            List of BM25SearchResult sorted descending by score.
        """
        if not self._bm25 or not self.chunks:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        # Collect candidate results with metadata filters
        allowed_items: set[str] | None = None
        if item_numbers:
            allowed_items = {i.upper() for i in item_numbers}
        elif item_number:
            allowed_items = {item_number.upper()}

        candidates: list[tuple[float, int]] = []
        for idx, score in enumerate(scores):
            if min_score is not None and score < min_score:
                continue


            chunk = self.chunks[idx]

            if cik and chunk.cik != cik:
                continue
            if accession_number and chunk.accession_number != accession_number:
                continue
            if allowed_items and chunk.item_number.upper() not in allowed_items:
                continue

            candidates.append((float(score), idx))

        # Sort descending by score
        candidates.sort(key=lambda x: x[0], reverse=True)

        results: list[BM25SearchResult] = []
        for rank, (score, idx) in enumerate(candidates[:n_results]):
            results.append(
                BM25SearchResult(
                    chunk=self.chunks[idx],
                    score=score,
                    rank=rank + 1,
                )
            )

        return results

    def clear(self) -> None:
        """Reset the index."""
        self.chunks.clear()
        self.corpus_tokens.clear()
        self._bm25 = None
        self._indexed_ids.clear()
