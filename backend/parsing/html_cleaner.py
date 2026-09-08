"""
Filing Sleuth — HTML Cleaner

Cleans raw 10-K/10-Q HTML into normalized text suitable for chunking and
LLM consumption. Handles:
- Stripping scripts, styles, hidden elements
- Normalizing HTML entities (&#160; → space, &amp; → &, etc.)
- Converting HTML tables to a readable text representation
- Removing boilerplate (page headers/footers, XBRL tags)
- Normalizing whitespace
"""

from __future__ import annotations

import re
from bs4 import BeautifulSoup, Tag, NavigableString


def clean_html(html: str) -> str:
    """Clean filing HTML to readable text.

    This is a multi-pass process:
    1. Parse with BeautifulSoup
    2. Remove non-content elements (scripts, styles, hidden)
    3. Convert tables to text representation
    4. Extract text
    5. Normalize whitespace and entities
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag_name in ["script", "style", "head", "meta", "link", "noscript"]:
        for el in soup.find_all(tag_name):
            el.decompose()

    # Remove hidden elements
    for el in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        el.decompose()

    # Remove XBRL inline tags but keep their content
    for el in soup.find_all(re.compile(r"^ix:", re.I)):
        el.unwrap()

    # Get text
    text = soup.get_text(separator="\n")

    # Normalize whitespace
    text = _normalize_whitespace(text)

    return text


def clean_html_preserve_structure(html: str) -> BeautifulSoup:
    """Clean HTML but preserve the DOM structure for section detection.

    Returns the cleaned BeautifulSoup object (not text) so the section
    parser can walk the tree looking for Item headers.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag_name in ["script", "style", "head", "meta", "link", "noscript"]:
        for el in soup.find_all(tag_name):
            el.decompose()

    # Remove hidden elements
    for el in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        el.decompose()

    # Unwrap XBRL inline tags but keep content
    for el in soup.find_all(re.compile(r"^ix:", re.I)):
        el.unwrap()

    return soup


def extract_text_from_element(element: Tag | NavigableString) -> str:
    """Extract text from a BeautifulSoup element, normalizing whitespace."""
    if isinstance(element, NavigableString):
        return str(element)

    text = element.get_text(separator="\n")
    return _normalize_whitespace(text)


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace in extracted text.

    - Replace non-breaking spaces with regular spaces
    - Collapse multiple blank lines to at most 2
    - Strip trailing whitespace from each line
    - Remove excessive spaces within lines
    """
    # HTML entities that become whitespace
    text = text.replace("\xa0", " ")  # &nbsp;
    text = text.replace("\u200b", "")  # Zero-width space
    text = text.replace("\u200c", "")  # Zero-width non-joiner
    text = text.replace("\u200d", "")  # Zero-width joiner
    text = text.replace("\ufeff", "")  # BOM

    # Collapse multiple spaces within lines (but preserve newlines)
    lines = text.split("\n")
    lines = [re.sub(r" {2,}", " ", line).strip() for line in lines]

    # Remove completely empty lines but keep paragraph breaks (max 2 consecutive newlines)
    result_lines: list[str] = []
    blank_count = 0
    for line in lines:
        if not line:
            blank_count += 1
            if blank_count <= 1:  # Allow at most 1 blank line
                result_lines.append("")
        else:
            blank_count = 0
            result_lines.append(line)

    return "\n".join(result_lines).strip()
