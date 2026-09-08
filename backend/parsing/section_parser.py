"""
Filing Sleuth — Section Parser

Parses 10-K/10-Q HTML to detect Item boundaries and extract each section.
This is structure-aware chunking — NOT fixed-size text chunks.

10-K Item structure:
  Part I:   Item 1 (Business), Item 1A (Risk Factors), Item 1B (Unresolved Staff Comments),
            Item 1C (Cybersecurity), Item 2 (Properties), Item 3 (Legal Proceedings),
            Item 4 (Mine Safety Disclosures)
  Part II:  Item 5 (Market Info), Item 6 (Reserved), Item 7 (MD&A),
            Item 7A (Quantitative Disclosures), Item 8 (Financial Statements),
            Item 9 (Changes in Accounting), Item 9A (Controls),
            Item 9B (Other Info), Item 9C (Foreign Jurisdictions)
  Part III: Item 10-14
  Part IV:  Item 15 (Exhibits), Item 16 (Form 10-K Summary)

IMPORTANT: 10-K formatting is genuinely inconsistent across companies and years.
Apple uses "Item 1.&#160;&#160;&#160;&#160;Business" in styled spans.
Tesla might use all-caps "ITEM 7." in bold tags.
Some filers use anchor tags with name attributes.
The parser needs multiple detection strategies with graceful fallback.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from backend.parsing.html_cleaner import clean_html_preserve_structure, extract_text_from_element

logger = logging.getLogger(__name__)


# Canonical Item definitions for 10-K
ITEM_DEFINITIONS: dict[str, str] = {
    "1": "Business",
    "1A": "Risk Factors",
    "1B": "Unresolved Staff Comments",
    "1C": "Cybersecurity",
    "2": "Properties",
    "3": "Legal Proceedings",
    "4": "Mine Safety Disclosures",
    "5": "Market for Registrant's Common Equity",
    "6": "Reserved",
    "7": "Management's Discussion and Analysis of Financial Condition and Results of Operations",
    "7A": "Quantitative and Qualitative Disclosures About Market Risk",
    "8": "Financial Statements and Supplementary Data",
    "9": "Changes in and Disagreements With Accountants on Accounting and Financial Disclosure",
    "9A": "Controls and Procedures",
    "9B": "Other Information",
    "9C": "Disclosure Regarding Foreign Jurisdictions that Prevent Inspections",
    "10": "Directors, Executive Officers and Corporate Governance",
    "11": "Executive Compensation",
    "12": "Security Ownership of Certain Beneficial Owners and Management",
    "13": "Certain Relationships and Related Transactions",
    "14": "Principal Accountant Fees and Services",
    "15": "Exhibits and Financial Statement Schedules",
    "16": "Form 10-K Summary",
}


@dataclass
class SectionLocation:
    """A detected Item section boundary in the filing HTML."""
    item_number: str        # e.g., "1A", "7"
    item_title: str         # e.g., "Risk Factors"
    char_offset: int        # Character offset in the raw HTML
    text_preview: str       # First ~200 chars of the section text
    detection_method: str   # How it was detected (for debugging)


@dataclass
class ParsedSection:
    """A fully extracted section of a filing."""
    item_number: str
    item_title: str
    text: str               # Full extracted text of the section
    char_offset_start: int
    char_offset_end: int
    word_count: int


@dataclass
class ParseResult:
    """Result of parsing a filing into sections."""
    sections: list[ParsedSection] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_text_length: int = 0
    items_found: list[str] = field(default_factory=list)
    detection_method: str = ""  # Which strategy succeeded


# ── Item header detection patterns ──────────────────────────────────────────

# Regex pattern for Item headers in text.
# Handles: "Item 1.", "ITEM 1A.", "Item 7A.", "Item 1C.", etc.
# The (?:&#160;|\xa0|\s)* handles non-breaking spaces between "Item" and the number.
# We require a period or colon or lots of spaces after the number to distinguish
# content headers from casual mentions ("see Item 7").
ITEM_HEADER_RE = re.compile(
    r"""
    (?:^|\n|\>)\s*                     # Start of line or after HTML tag
    (?:PART\s+[IVX]+[\.\s]*)?         # Optional "Part I" prefix
    Item\s*                           # "Item" keyword
    (?:&\#160;|&nbsp;|\xa0|\s)*       # Various non-breaking spaces
    (\d+[A-Ca-c]?)                    # Item number (1, 1A, 7, 7A, etc.)
    \s*[\.:\-—]?\s*                   # Separator (period, colon, dash)
    (?:&\#160;|&nbsp;|\xa0|\s)*       # More possible spaces
    ([^\n<]{0,120}?)                  # Title text (up to 120 chars)
    \s*(?:\n|<|$)                     # End of line or HTML tag
    """,
    re.IGNORECASE | re.VERBOSE | re.MULTILINE,
)

# Pattern for Table of Contents entries (we want to SKIP these, not treat as content)
TOC_INDICATORS = re.compile(
    r"(?i)(table\s+of\s+contents|index|page\s+\d+|\b\d+\s*$)",
)


class SectionParser:
    """Parse 10-K/10-Q HTML into Item-level sections.

    Usage:
        parser = SectionParser()
        result = parser.parse(html_content)
        for section in result.sections:
            print(f"Item {section.item_number}: {section.item_title} ({section.word_count} words)")
    """

    # Items that typically have the most useful content for financial analysis
    HIGH_VALUE_ITEMS = {"1A", "7", "7A", "8"}

    def parse(self, html: str, form_type: str = "10-K") -> ParseResult:
        """Parse a filing HTML into sections.

        Args:
            html: Raw HTML of the filing document.
            form_type: "10-K" or "10-Q" (affects expected Item structure).

        Returns:
            ParseResult with extracted sections and any warnings.
        """
        result = ParseResult(total_text_length=len(html))

        # Strategy 1: Regex-based detection on raw HTML (fastest, works for most filings)
        locations = self._detect_items_regex(html)

        if len(locations) >= 3:
            # Good detection — filter to content sections (skip ToC)
            content_locations = self._filter_toc_entries(locations, html)
            if len(content_locations) >= 3:
                locations = content_locations
                result.detection_method = "regex_filtered"
            else:
                result.detection_method = "regex_unfiltered"

            # Extract text between detected boundaries
            result.sections = self._extract_sections(html, locations)
            result.items_found = [s.item_number for s in result.sections]

            logger.info(
                "Parsed %d sections using %s: %s",
                len(result.sections),
                result.detection_method,
                ", ".join(f"Item {s.item_number}" for s in result.sections),
            )
        else:
            # Strategy 2: Fallback — treat entire filing as one section
            result.warnings.append(
                f"Could not detect Item boundaries (found only {len(locations)} headers). "
                f"Falling back to single-section mode."
            )
            result.detection_method = "fallback_single_section"

            from backend.parsing.html_cleaner import clean_html
            full_text = clean_html(html)
            result.sections = [
                ParsedSection(
                    item_number="FULL",
                    item_title="Complete Filing",
                    text=full_text,
                    char_offset_start=0,
                    char_offset_end=len(html),
                    word_count=len(full_text.split()),
                )
            ]
            result.items_found = ["FULL"]

            logger.warning(
                "Fallback: filing treated as single section (%d words)",
                result.sections[0].word_count,
            )

        return result

    def _detect_items_regex(self, html: str) -> list[SectionLocation]:
        """Detect Item headers using regex on raw HTML."""
        locations: list[SectionLocation] = []
        seen_items: set[str] = set()

        for match in ITEM_HEADER_RE.finditer(html):
            item_num = match.group(1).upper()
            title_text = match.group(2).strip() if match.group(2) else ""

            # Clean up title
            title_text = re.sub(r"&\#\d+;", " ", title_text)  # Remove HTML entities
            title_text = re.sub(r"\s+", " ", title_text).strip()
            title_text = title_text.rstrip(".")

            # Validate: is this a known Item number?
            if item_num not in ITEM_DEFINITIONS:
                continue

            # Use canonical title if extracted title is empty or too short
            canonical_title = ITEM_DEFINITIONS[item_num]
            if len(title_text) < 3:
                title_text = canonical_title

            location = SectionLocation(
                item_number=item_num,
                item_title=title_text,
                char_offset=match.start(),
                text_preview=html[match.start():match.start() + 200],
                detection_method="regex",
            )
            locations.append(location)

        return locations

    def _filter_toc_entries(
        self,
        locations: list[SectionLocation],
        html: str,
    ) -> list[SectionLocation]:
        """Filter out Table of Contents entries and running headers,
        keeping only the true start of each content section.

        In SEC filings:
        1. The Table of Contents (ToC) lists items sequentially (e.g. 1, 1A, ..., 16).
           When the body begins, the item numbers reset back to 1 (or 1A).
        2. Within the body, running page headers repeat the current Item number on
           every single page break (e.g., Item 7 appears 15 times).
        3. Therefore:
           a) Detect any ToC sequence by looking for a rank reset (e.g. from >= Item 7
              back down to Item 1/1A).
           b) Discard all ToC matches before that reset.
           c) Within the body matches, select only the FIRST occurrence of each item
              that monotonically advances the Item rank, skipping running headers.
        """
        if len(locations) < 3:
            return locations

        item_order = list(ITEM_DEFINITIONS.keys())
        item_to_rank = {item: i for i, item in enumerate(item_order)}

        # Step 1: Detect ToC reset
        toc_cutoff_index = 0
        max_seen_rank = -1
        for i, loc in enumerate(locations):
            rank = item_to_rank.get(loc.item_number, -1)
            if rank < 0:
                continue
            # If we have reached at least Item 7 or higher, and see a reset to Item 1 or 1A,
            # that is the transition from the Table of Contents to the Document Body.
            if max_seen_rank >= item_to_rank.get("7", 9) and rank <= item_to_rank.get("1A", 1):
                logger.debug(
                    "Detected ToC reset at match %d (offset %d): rank %d -> %d",
                    i, loc.char_offset, max_seen_rank, rank,
                )
                toc_cutoff_index = i
                break
            if rank > max_seen_rank:
                max_seen_rank = rank

        body_locations = locations[toc_cutoff_index:]

        # Step 2: Extract strictly advancing item sections in the body.
        # This naturally ignores running headers (which have rank <= current_rank).
        content_locations: list[SectionLocation] = []
        current_rank = -1
        for loc in body_locations:
            rank = item_to_rank.get(loc.item_number, -1)
            if rank > current_rank:
                content_locations.append(loc)
                current_rank = rank

        return content_locations


    def _extract_sections(
        self,
        html: str,
        locations: list[SectionLocation],
    ) -> list[ParsedSection]:
        """Extract text between detected Item boundaries."""
        from backend.parsing.html_cleaner import clean_html

        sections: list[ParsedSection] = []

        for i, loc in enumerate(locations):
            start = loc.char_offset
            # End at the next item's start, or end of document
            end = locations[i + 1].char_offset if i + 1 < len(locations) else len(html)

            # Extract and clean the HTML for this section
            section_html = html[start:end]
            section_text = clean_html(section_html)

            # Skip very short sections (likely just a cross-reference)
            if len(section_text.split()) < 20:
                logger.debug(
                    "Skipping very short section Item %s (%d words)",
                    loc.item_number, len(section_text.split()),
                )
                continue

            section = ParsedSection(
                item_number=loc.item_number,
                item_title=loc.item_title or ITEM_DEFINITIONS.get(loc.item_number, ""),
                text=section_text,
                char_offset_start=start,
                char_offset_end=end,
                word_count=len(section_text.split()),
            )
            sections.append(section)

        return sections
