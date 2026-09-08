"""
Filing Sleuth — Hybrid Search Engine

Combines dense vector retrieval (ChromaDB) and sparse keyword retrieval (BM25)
using Reciprocal Rank Fusion (RRF).

Why Hybrid?
- Vector search excels at conceptual/semantic intent ("antitrust regulatory scrutiny",
  "supply chain vulnerabilities", "headcount changes").
- BM25 excels at exact keyword precision, acronyms, product lines, and GAAP line items
  ("ASC 606", "Qualcomm litigation", "FSD Supervised", "Titan").
- Reciprocal Rank Fusion ensures neither method dominates while rewarding chunks
  ranked highly by both.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.indexing.bm25_index import BM25Index
from backend.indexing.vector_store import VectorStore
from backend.parsing.chunk_builder import SectionChunk

logger = logging.getLogger(__name__)

# Standard RRF constant (Cormack et al.)
DEFAULT_RRF_K = 60


@dataclass
class HybridSearchResult:
    """A scored result from hybrid vector + BM25 search with full citation provenance."""
    chunk_id: str
    text: str
    company: str
    cik: str
    accession_number: str
    form_type: str
    filing_date: str
    reporting_date: str
    item_number: str
    item_title: str
    word_count: int
    rrf_score: float
    vector_rank: int | None = None
    bm25_rank: int | None = None
    vector_distance: float | None = None
    bm25_score: float | None = None


class HybridSearchEngine:
    """Orchestrates indexing and fused retrieval across Vector and BM25 indexes.

    Usage:
        engine = HybridSearchEngine(vector_store, bm25_index)
        engine.index_filing_chunks(chunks)
        results = engine.search(
            query="Qualcomm antitrust litigation",
            item_number="1A",
            n_results=5,
        )
    """

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        bm25_index: BM25Index | None = None,
        rrf_k: int = DEFAULT_RRF_K,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
    ) -> None:
        self.vector_store = vector_store or VectorStore()
        self.bm25_index = bm25_index or BM25Index()
        self.rrf_k = rrf_k
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        # Keep an in-memory lookup from chunk_id to SectionChunk for rich metadata
        self._chunks_by_id: dict[str, SectionChunk] = {}

    def index_filing_chunks(self, chunks: list[SectionChunk]) -> dict[str, int]:
        """Index chunks into both vector store and BM25 index."""
        if not chunks:
            return {"vector": 0, "bm25": 0}

        for c in chunks:
            self._chunks_by_id[c.chunk_id] = c

        bm25_count = self.bm25_index.index_chunks(chunks)
        vector_count = self.vector_store.add_chunks(chunks)

        logger.info(
            "HybridSearchEngine indexed %d chunks (BM25: %d, Vector: %d)",
            len(chunks), bm25_count, vector_count,
        )
        return {"vector": vector_count, "bm25": bm25_count}

    def search(
        self,
        query: str,
        n_results: int = 10,
        *,
        cik: str | None = None,
        accession_number: str | None = None,
        item_number: str | None = None,
        item_numbers: list[str] | None = None,
        pool_factor: int = 3,
    ) -> list[HybridSearchResult]:
        """Execute hybrid search using Reciprocal Rank Fusion.

        Args:
            query: Natural language or keyword query.
            n_results: Number of final fused results to return.
            cik: Optional CIK filter.
            accession_number: Optional accession number filter.
            item_number: Optional single Item number filter (e.g. "1A", "7").
            item_numbers: Optional list of Item numbers to filter.
            pool_factor: Over-fetch factor for individual searches before fusion.

        Returns:
            List of HybridSearchResult sorted descending by RRF score.
        """
        fetch_k = n_results * pool_factor

        # 1. Dense vector search
        vector_results = self.vector_store.search(
            query=query,
            n_results=fetch_k,
            cik=cik,
            accession_number=accession_number,
            item_number=item_number,
            item_numbers=item_numbers,
        )

        # 2. Sparse BM25 search
        bm25_results = self.bm25_index.search(
            query=query,
            n_results=fetch_k,
            cik=cik,
            accession_number=accession_number,
            item_number=item_number,
            item_numbers=item_numbers,
        )

        # 3. Reciprocal Rank Fusion
        fused_scores: dict[str, float] = {}
        v_rank_map: dict[str, int] = {}
        v_dist_map: dict[str, float] = {}
        b_rank_map: dict[str, int] = {}
        b_score_map: dict[str, float] = {}

        for vr in vector_results:
            cid = vr.chunk_id
            v_rank_map[cid] = vr.rank
            v_dist_map[cid] = vr.distance
            fused_scores[cid] = fused_scores.get(cid, 0.0) + self.vector_weight / (self.rrf_k + vr.rank)

        for br in bm25_results:
            cid = br.chunk.chunk_id
            b_rank_map[cid] = br.rank
            b_score_map[cid] = br.score
            fused_scores[cid] = fused_scores.get(cid, 0.0) + self.bm25_weight / (self.rrf_k + br.rank)

        # Sort chunk IDs by fused RRF score descending
        sorted_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)

        # Build output results
        results: list[HybridSearchResult] = []
        for cid in sorted_ids[:n_results]:
            chunk = self._chunks_by_id.get(cid)
            if chunk:
                results.append(
                    HybridSearchResult(
                        chunk_id=chunk.chunk_id,
                        text=chunk.text,
                        company=chunk.company,
                        cik=chunk.cik,
                        accession_number=chunk.accession_number,
                        form_type=chunk.form_type,
                        filing_date=chunk.filing_date,
                        reporting_date=chunk.reporting_date,
                        item_number=chunk.item_number,
                        item_title=chunk.item_title,
                        word_count=chunk.word_count,
                        rrf_score=fused_scores[cid],
                        vector_rank=v_rank_map.get(cid),
                        bm25_rank=b_rank_map.get(cid),
                        vector_distance=v_dist_map.get(cid),
                        bm25_score=b_score_map.get(cid),
                    )
                )
            else:
                # Fallback if chunk not in memory map: use vector result metadata if present
                v_match = next((v for v in vector_results if v.chunk_id == cid), None)
                if v_match:
                    meta = v_match.metadata
                    results.append(
                        HybridSearchResult(
                            chunk_id=cid,
                            text=v_match.text,
                            company=meta.get("company", ""),
                            cik=meta.get("cik", ""),
                            accession_number=meta.get("accession_number", ""),
                            form_type=meta.get("form_type", "10-K"),
                            filing_date=meta.get("filing_date", ""),
                            reporting_date=meta.get("reporting_date", ""),
                            item_number=meta.get("item_number", ""),
                            item_title=meta.get("item_title", ""),
                            word_count=int(meta.get("word_count", 0)),
                            rrf_score=fused_scores[cid],
                            vector_rank=v_rank_map.get(cid),
                            bm25_rank=b_rank_map.get(cid),
                            vector_distance=v_dist_map.get(cid),
                            bm25_score=b_score_map.get(cid),
                        )
                    )

        return results
