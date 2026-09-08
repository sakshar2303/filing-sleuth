"""
Filing Sleuth — Chunk Builder

Takes parsed sections and produces metadata-tagged chunks suitable for
indexing and retrieval. Each chunk is a self-contained unit with full
provenance metadata (company, accession number, fiscal period, item, etc.).

Sections that exceed a maximum token length are split at paragraph boundaries
to keep each chunk within the LLM context window budget. Metadata is
propagated to every sub-chunk.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from backend.parsing.section_parser import ParsedSection, ITEM_DEFINITIONS

logger = logging.getLogger(__name__)

# Approximate tokens-per-character ratio for English financial text.
# Roughly 1 token ≈ 4 characters. We use this for a rough token estimate.
CHARS_PER_TOKEN = 4

# Maximum chunk size in tokens. We target ~3000 tokens to leave room for
# the prompt, system instructions, and response within a 4K-8K token budget.
MAX_CHUNK_TOKENS = 3000
MAX_CHUNK_CHARS = MAX_CHUNK_TOKENS * CHARS_PER_TOKEN  # ~12000 chars


@dataclass
class SectionChunk:
    """A metadata-tagged chunk ready for indexing.

    This is the atomic unit that goes into the vector store and BM25 index.
    Every chunk has full provenance so citations can be traced back to source.
    """
    chunk_id: str               # Unique identifier
    company: str                # Company name (e.g., "Apple Inc.")
    cik: str                    # 10-digit CIK
    accession_number: str       # Filing accession number
    form_type: str              # "10-K" or "10-Q"
    fiscal_year: int | None     # Fiscal year (if known)
    fiscal_period: str          # "FY", "Q1", etc.
    filing_date: str            # Date filed
    reporting_date: str         # Period end date
    item_number: str            # "1A", "7", "8", etc.
    item_title: str             # "Risk Factors", "MD&A", etc.
    chunk_index: int            # 0-indexed within this section
    total_chunks_in_section: int
    text: str                   # The actual chunk text
    char_offset_start: int      # Position in original HTML
    char_offset_end: int        # Position in original HTML
    word_count: int
    token_estimate: int         # Approximate token count


@dataclass
class FilingMetadata:
    """Metadata about the filing being chunked."""
    company: str
    cik: str
    accession_number: str
    form_type: str
    fiscal_year: int | None = None
    fiscal_period: str = "FY"
    filing_date: str = ""
    reporting_date: str = ""


class ChunkBuilder:
    """Build metadata-tagged chunks from parsed sections.

    Usage:
        builder = ChunkBuilder()
        chunks = builder.build_chunks(
            sections=parsed_result.sections,
            metadata=FilingMetadata(
                company="Apple Inc.",
                cik="0000320193",
                accession_number="0000320193-23-000106",
                form_type="10-K",
                fiscal_year=2023,
                filing_date="2023-11-03",
                reporting_date="2023-09-30",
            ),
        )
    """

    def __init__(
        self,
        max_chunk_chars: int = MAX_CHUNK_CHARS,
    ) -> None:
        self.max_chunk_chars = max_chunk_chars

    def build_chunks(
        self,
        sections: list[ParsedSection],
        metadata: FilingMetadata,
    ) -> list[SectionChunk]:
        """Build chunks from all sections of a filing.

        Sections that fit within max_chunk_chars become a single chunk.
        Sections that are too long are split at paragraph boundaries.
        """
        all_chunks: list[SectionChunk] = []

        for section in sections:
            section_chunks = self._chunk_section(section, metadata)
            all_chunks.extend(section_chunks)

        logger.info(
            "Built %d chunks from %d sections for %s (CIK %s, accession %s)",
            len(all_chunks),
            len(sections),
            metadata.company,
            metadata.cik,
            metadata.accession_number,
        )
        return all_chunks

    def _chunk_section(
        self,
        section: ParsedSection,
        metadata: FilingMetadata,
    ) -> list[SectionChunk]:
        """Split a single section into chunks if needed."""

        text = section.text

        if len(text) <= self.max_chunk_chars:
            # Section fits in one chunk
            chunk = self._make_chunk(
                text=text,
                section=section,
                metadata=metadata,
                chunk_index=0,
                total_chunks=1,
            )
            return [chunk]

        # Section is too long — split at paragraph boundaries
        paragraphs = self._split_paragraphs(text)
        chunks: list[SectionChunk] = []
        current_text = ""
        chunk_texts: list[str] = []

        for para in paragraphs:
            if len(current_text) + len(para) + 2 > self.max_chunk_chars and current_text:
                # Current chunk is full — save it
                chunk_texts.append(current_text)
                current_text = para
            else:
                if current_text:
                    current_text += "\n\n" + para
                else:
                    current_text = para

        # Don't forget the last chunk
        if current_text:
            chunk_texts.append(current_text)

        # Handle edge case: a single paragraph exceeds max size
        # Split it at sentence boundaries
        final_texts: list[str] = []
        for ct in chunk_texts:
            if len(ct) > self.max_chunk_chars:
                final_texts.extend(self._split_at_sentences(ct))
            else:
                final_texts.append(ct)

        total = len(final_texts)
        for i, text in enumerate(final_texts):
            chunk = self._make_chunk(
                text=text,
                section=section,
                metadata=metadata,
                chunk_index=i,
                total_chunks=total,
            )
            chunks.append(chunk)

        return chunks

    def _make_chunk(
        self,
        text: str,
        section: ParsedSection,
        metadata: FilingMetadata,
        chunk_index: int,
        total_chunks: int,
    ) -> SectionChunk:
        """Create a SectionChunk with full metadata."""
        # Build a unique chunk ID
        item_key = section.item_number.replace(" ", "")
        chunk_id = (
            f"{metadata.cik}_{metadata.accession_number}"
            f"_item{item_key}_chunk{chunk_index}"
        )

        return SectionChunk(
            chunk_id=chunk_id,
            company=metadata.company,
            cik=metadata.cik,
            accession_number=metadata.accession_number,
            form_type=metadata.form_type,
            fiscal_year=metadata.fiscal_year,
            fiscal_period=metadata.fiscal_period,
            filing_date=metadata.filing_date,
            reporting_date=metadata.reporting_date,
            item_number=section.item_number,
            item_title=section.item_title or ITEM_DEFINITIONS.get(section.item_number, ""),
            chunk_index=chunk_index,
            total_chunks_in_section=total_chunks,
            text=text,
            char_offset_start=section.char_offset_start,
            char_offset_end=section.char_offset_end,
            word_count=len(text.split()),
            token_estimate=len(text) // CHARS_PER_TOKEN,
        )

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        """Split text into paragraphs (separated by blank lines)."""
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    @staticmethod
    def _split_at_sentences(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
        """Split a long text at sentence boundaries as a last resort."""
        # Simple sentence boundary detection
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[str] = []
        current = ""

        for sent in sentences:
            if len(current) + len(sent) + 1 > max_chars and current:
                chunks.append(current)
                current = sent
            else:
                current = current + " " + sent if current else sent

        if current:
            chunks.append(current)

        return chunks
