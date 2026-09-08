"""
Unit tests for backend.agent.extraction_agent.
"""

import pytest
from backend.agent.extraction_agent import ExtractionAgent, normalize_metric_name
from backend.agent.query_planner import SubQuestion
from backend.indexing.bm25_index import BM25Index
from backend.indexing.hybrid_search import HybridSearchEngine
from backend.indexing.vector_store import VectorStore
from backend.parsing.chunk_builder import SectionChunk


def make_chunk(chunk_id: str, text: str, item_number: str = "1C", cik: str = "0000789019") -> SectionChunk:
    return SectionChunk(
        chunk_id=chunk_id,
        company="MICROSOFT CORP",
        cik=cik,
        accession_number="0001193125-26-323660",
        form_type="10-K",
        fiscal_year=2026,
        fiscal_period="FY",
        filing_date="2026-07-29",
        reporting_date="2026-06-30",
        item_number=item_number,
        item_title="Cybersecurity",
        chunk_index=0,
        total_chunks_in_section=1,
        text=text,
        char_offset_start=0,
        char_offset_end=len(text),
        word_count=len(text.split()),
        token_estimate=len(text) // 4,
    )


def test_normalize_metric_name():
    assert normalize_metric_name("ResearchAndDevelopmentExpense") == "research_and_development"
    assert normalize_metric_name("Revenues") == "revenue"
    assert normalize_metric_name("NetIncomeLoss") == "net_income"
    assert normalize_metric_name("GrossProfit") == "gross_profit"


@pytest.mark.asyncio
async def test_extraction_from_text_with_quote_verification(tmp_path):
    vector_store = VectorStore(persist_dir=tmp_path / "chroma")
    bm25_index = BM25Index()
    engine = HybridSearchEngine(vector_store, bm25_index)

    text = (
        "Microsoft plays a central role in the world's digital ecosystem. "
        "We have made it a top corporate priority to protect the company and partners from cybersecurity threats."
    )
    chunk = make_chunk("c1", text, item_number="1C", cik="0000789019")
    engine.index_filing_chunks([chunk])

    agent = ExtractionAgent(search_engine=engine)
    sq = SubQuestion(
        id="sq_1",
        text="What cybersecurity priority did Microsoft disclose?",
        company_ticker="MSFT",
        company_name="MICROSOFT CORP",
        cik="0000789019",
        source_preference="TEXT",
        target_item="1C",
    )

    fact = await agent.extract(sq)
    assert fact.status == "FOUND"
    assert fact.source_type == "TEXT"
    assert fact.quote_verified is True
    assert fact.quote_verification_score is not None
    assert fact.quote_verification_score >= 80.0
