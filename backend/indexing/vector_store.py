"""
Filing Sleuth — ChromaDB Vector Store

Provides dense vector semantic search over metadata-tagged filing chunks.
Uses SentenceTransformers (all-MiniLM-L6-v2) for embeddings and ChromaDB
for persistent vector indexing and metadata filtering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from backend.config import get_settings
from backend.parsing.chunk_builder import SectionChunk

logger = logging.getLogger(__name__)


@dataclass
class VectorSearchResult:
    """A scored search result from the vector store."""
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    distance: float  # Cosine / L2 distance (lower = more similar)
    rank: int


class VectorStore:
    """ChromaDB-backed vector store for SEC filing chunks.

    Usage:
        store = VectorStore()
        store.add_chunks(chunks)
        results = store.search("autonomous driving risk factors", n_results=5, item_number="1A")
    """

    COLLECTION_NAME = "sec_filing_chunks"

    def __init__(self, persist_dir: Path | str | None = None) -> None:
        settings = get_settings()
        if persist_dir is None:
            persist_dir = settings.chroma_db_path

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model,
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Initialized VectorStore at %s (collection: %s, existing items: %d)",
            self.persist_dir,
            self.COLLECTION_NAME,
            self._collection.count(),
        )

    def count(self) -> int:
        """Return total number of chunks in the vector collection."""
        return self._collection.count()

    def add_chunks(self, chunks: list[SectionChunk], batch_size: int = 64) -> int:
        """Add chunks to the vector store with upsert to avoid duplicates.

        Args:
            chunks: List of SectionChunk objects.
            batch_size: Embedding batch size.

        Returns:
            Number of chunks upserted.
        """
        if not chunks:
            return 0

        total_upserted = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            ids = [c.chunk_id for c in batch]
            documents = [
                f"Item {c.item_number} ({c.item_title})\nCompany: {c.company} | Form: {c.form_type} | Period: {c.reporting_date}\n\n{c.text}"
                for c in batch
            ]
            metadatas = [
                {
                    "chunk_id": c.chunk_id,
                    "company": c.company,
                    "cik": c.cik,
                    "accession_number": c.accession_number,
                    "form_type": c.form_type,
                    "fiscal_year": c.fiscal_year if c.fiscal_year is not None else 0,
                    "fiscal_period": c.fiscal_period,
                    "filing_date": c.filing_date,
                    "reporting_date": c.reporting_date,
                    "item_number": c.item_number,
                    "item_title": c.item_title,
                    "chunk_index": c.chunk_index,
                    "total_chunks": c.total_chunks_in_section,
                    "word_count": c.word_count,
                }
                for c in batch
            ]

            self._collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            total_upserted += len(batch)

        logger.info(
            "Upserted %d chunks into VectorStore (total now: %d)",
            total_upserted, self._collection.count(),
        )
        return total_upserted

    def search(
        self,
        query: str,
        n_results: int = 10,
        *,
        cik: str | None = None,
        accession_number: str | None = None,
        item_number: str | None = None,
        item_numbers: list[str] | None = None,
    ) -> list[VectorSearchResult]:
        """Search the vector store for chunks semantically similar to query.

        Args:
            query: Natural language query.
            n_results: Maximum results to return.
            cik: Optional CIK filter.
            accession_number: Optional accession number filter.
            item_number: Optional single Item number filter.
            item_numbers: Optional list of Item numbers to filter.

        Returns:
            List of VectorSearchResult sorted ascending by cosine distance.
        """
        if self._collection.count() == 0:
            return []

        # Build Chroma where filter
        where_clauses: list[dict[str, Any]] = []

        if cik:
            where_clauses.append({"cik": cik})
        if accession_number:
            where_clauses.append({"accession_number": accession_number})
        if item_numbers:
            if len(item_numbers) == 1:
                where_clauses.append({"item_number": item_numbers[0]})
            else:
                where_clauses.append({"item_number": {"$in": item_numbers}})
        elif item_number:
            where_clauses.append({"item_number": item_number})

        where_filter: dict[str, Any] | None = None
        if len(where_clauses) == 1:
            where_filter = where_clauses[0]
        elif len(where_clauses) > 1:
            where_filter = {"$and": where_clauses}

        limit = min(n_results, self._collection.count())
        if limit <= 0:
            return []

        query_kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": limit,
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        raw = self._collection.query(**query_kwargs)

        results: list[VectorSearchResult] = []
        if not raw or not raw.get("ids") or not raw["ids"][0]:
            return results

        ids = raw["ids"][0]
        documents = raw["documents"][0] if raw.get("documents") else [""] * len(ids)
        metadatas = raw["metadatas"][0] if raw.get("metadatas") else [{}] * len(ids)
        distances = raw["distances"][0] if raw.get("distances") else [0.0] * len(ids)

        for rank, (cid, doc, meta, dist) in enumerate(zip(ids, documents, metadatas, distances)):
            results.append(
                VectorSearchResult(
                    chunk_id=cid,
                    text=doc,
                    metadata=meta,
                    distance=dist,
                    rank=rank + 1,
                )
            )

        return results

    def clear(self) -> None:
        """Reset the collection."""
        self._client.delete_collection(self.COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
