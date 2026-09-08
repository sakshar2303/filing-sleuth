"""
Unit tests for backend.indexing.hybrid_search.
"""

import pytest
from backend.indexing.bm25_index import BM25Index
from backend.indexing.hybrid_search import HybridSearchEngine, DEFAULT_RRF_K
from backend.indexing.vector_store import VectorStore
from backend.parsing.chunk_builder import SectionChunk


def make_chunk(chunk_id: str, text: str, item_number: str = "7", cik: str = "0000320193") -> SectionChunk:
    return SectionChunk(
        chunk_id=chunk_id,
        company="Test Corp",
        cik=cik,
        accession_number="0000320193-25-000001",
        form_type="10-K",
        fiscal_year=2025,
        fiscal_period="FY",
        filing_date="2025-10-31",
        reporting_date="2025-09-30",
        item_number=item_number,
        item_title="Section Title",
        chunk_index=0,
        total_chunks_in_section=1,
        text=text,
        char_offset_start=0,
        char_offset_end=len(text),
        word_count=len(text.split()),
        token_estimate=len(text) // 4,
    )


def test_hybrid_search_fusion(tmp_path):
    # Use isolated test directory for ChromaDB
    vector_store = VectorStore(persist_dir=tmp_path / "chroma")
    bm25_index = BM25Index()
    engine = HybridSearchEngine(vector_store=vector_store, bm25_index=bm25_index)

    c1 = make_chunk("c1", "Autonomous driving neural networks and FSD safety validations for electric vehicles.", item_number="1")
    c2 = make_chunk("c2", "Battery supply contracts and lithium refining facility investments in Texas.", item_number="7")
    c3 = make_chunk("c3", "Risk factors regarding autonomous driving safety investigations and NHTSA recalls.", item_number="1A")

    engine.index_filing_chunks([c1, c2, c3])

    results = engine.search("autonomous driving safety NHTSA", n_results=3)
    assert len(results) > 0
    # c3 mentions both "autonomous driving" and exact "NHTSA"
    top_hit = results[0]
    assert top_hit.chunk_id in ["c3", "c1"]
    assert top_hit.rrf_score > 0
    assert top_hit.company == "Test Corp"


def test_hybrid_search_filtering(tmp_path):
    vector_store = VectorStore(persist_dir=tmp_path / "chroma_filter")
    bm25_index = BM25Index()
    engine = HybridSearchEngine(vector_store=vector_store, bm25_index=bm25_index)

    c1 = make_chunk("c1", "Litigation regarding mobile App Store.", item_number="3", cik="0000320193")
    c2 = make_chunk("c2", "Risk factors concerning mobile App Store commissions.", item_number="1A", cik="0000320193")
    c3 = make_chunk("c3", "Cloud Azure revenues growing rapidly.", item_number="7", cik="0000789019")

    engine.index_filing_chunks([c1, c2, c3])

    # Filter to CIK 0000320193
    res_aapl = engine.search("mobile", cik="0000320193")
    for r in res_aapl:
        assert r.cik == "0000320193"

    # Filter to item_number "1A"
    res_item = engine.search("App Store", item_number="1A")
    for r in res_item:
        assert r.item_number == "1A"
