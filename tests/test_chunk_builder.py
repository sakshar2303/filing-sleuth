"""
Unit tests for backend.parsing.chunk_builder.
"""

import pytest
from backend.parsing.section_parser import ParsedSection
from backend.parsing.chunk_builder import ChunkBuilder, FilingMetadata, SectionChunk



def test_chunk_builder_basic():
    builder = ChunkBuilder(max_chunk_chars=500)
    meta = FilingMetadata(
        company="Apple Inc.",
        cik="0000320193",
        accession_number="0000320193-25-000079",
        form_type="10-K",
        filing_date="2025-10-31",
        reporting_date="2025-09-27",
    )

    # 250 words section, ~1500 chars, so should be split when max_chunk_chars=500
    words = ["word" + str(i) for i in range(250)]
    section_text = "\n\n".join(" ".join(words[i:i+20]) for i in range(0, 250, 20))
    section = ParsedSection(
        item_number="7",
        item_title="Management's Discussion and Analysis",
        text=section_text,
        char_offset_start=0,
        char_offset_end=len(section_text),
        word_count=250,
    )

    chunks = builder.build_chunks([section], meta)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.item_number == "7"
        assert chunk.company == "Apple Inc."
        assert chunk.cik == "0000320193"
        assert chunk.accession_number == "0000320193-25-000079"
        assert chunk.chunk_id.startswith(f"{meta.cik}_{meta.accession_number}_item7_chunk")


def test_chunk_builder_short_section():
    builder = ChunkBuilder(max_chunk_chars=12000)
    meta = FilingMetadata(
        company="Tesla, Inc.",
        cik="0001318605",
        accession_number="0001628280-26-003952",
        form_type="10-K",
        filing_date="2026-01-29",
        reporting_date="2025-12-31",
    )

    section_text = "Tesla cybersecurity risk management program is integrated into enterprise risk processes."
    section = ParsedSection(
        item_number="1C",
        item_title="Cybersecurity",
        text=section_text,
        char_offset_start=0,
        char_offset_end=len(section_text),
        word_count=len(section_text.split()),
    )

    chunks = builder.build_chunks([section], meta)
    assert len(chunks) == 1
    assert chunks[0].item_number == "1C"
    assert chunks[0].word_count == len(section_text.split())

