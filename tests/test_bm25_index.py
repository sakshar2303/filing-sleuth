"""
Unit tests for backend.indexing.bm25_index.
"""

import pytest
from backend.indexing.bm25_index import BM25Index, tokenize
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


def test_tokenize():
    tokens = tokenize("Apple Inc. reports $100M revenue in 2025!")
    assert "apple" in tokens
    assert "inc" in tokens
    assert "reports" in tokens
    assert "revenue" in tokens
    assert "2025" in tokens
    # Stopword filtered
    assert "in" not in tokens


def test_bm25_search_ranking():
    index = BM25Index()
    c1 = make_chunk("c1", "Apple reported strong iPhone and iPad sales across Europe and China.")
    c2 = make_chunk("c2", "Qualcomm patent licensing litigation with Apple regarding wireless modem chips.")
    c3 = make_chunk("c3", "The company faces supply chain logistics delays in semiconductor fabrication.")

    index.index_chunks([c1, c2, c3])

    res = index.search("Qualcomm patent modem", n_results=3)
    assert len(res) > 0
    assert res[0].chunk.chunk_id == "c2"
    assert res[0].score > 0


def test_bm25_metadata_filter():
    index = BM25Index()
    c1 = make_chunk("c1", "Litigation regarding mobile antitrust in App Store.", item_number="3", cik="0000320193")
    c2 = make_chunk("c2", "Risk factors concerning antitrust regulatory scrutiny in Europe.", item_number="1A", cik="0000320193")
    c3 = make_chunk("c3", "Antitrust regulations impacting cloud services segment.", item_number="1A", cik="0000789019")

    index.index_chunks([c1, c2, c3])

    # Filter by item_number="1A"
    res = index.search("antitrust", item_number="1A")
    for r in res:
        assert r.chunk.item_number == "1A"

    # Filter by CIK
    res_cik = index.search("antitrust", cik="0000789019")
    assert len(res_cik) == 1
    assert res_cik[0].chunk.chunk_id == "c3"


def test_bm25_empty_index():
    index = BM25Index()
    res = index.search("anything")
    assert res == []
