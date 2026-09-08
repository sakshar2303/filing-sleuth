"""
Unit tests for backend.parsing.section_parser.
"""

import pytest
from backend.parsing.section_parser import SectionParser, ITEM_DEFINITIONS


def test_section_parser_item_definitions():
    assert "1" in ITEM_DEFINITIONS
    assert "1A" in ITEM_DEFINITIONS
    assert "7" in ITEM_DEFINITIONS
    assert "8" in ITEM_DEFINITIONS
    assert ITEM_DEFINITIONS["1"] == "Business"
    assert ITEM_DEFINITIONS["1A"] == "Risk Factors"


def test_section_parser_toc_and_body():
    # Synthetic HTML mimicking 10-K with ToC and body with repeated running headers
    sample_html = """
    <html><body>
    <div id="toc">
        <p>TABLE OF CONTENTS</p>
        <p>Item 1. Business ................. 1</p>
        <p>Item 1A. Risk Factors ........... 5</p>
        <p>Item 7. Management's Discussion . 10</p>
        <p>Item 8. Financial Statements .... 20</p>
    </div>
    <div id="body">
        <h1>PART I</h1>
        <h2>Item 1. Business</h2>
        <p>Apple Inc. designs, manufactures and markets smartphones, personal computers, tablets, wearables and accessories, and sells a variety of related services.</p>
        <p>Item 1. Business (running header)</p>
        <p>More business text describing products and services in extensive detail with over thirty words to satisfy the minimum threshold.</p>
        
        <h2>Item 1A. Risk Factors</h2>
        <p>The company's business, reputation, results of operations and financial condition could be materially adversely affected by various risks including supply chain disruptions, geopolitical conflicts, and regulatory scrutiny across global markets.</p>
        
        <h1>PART II</h1>
        <h2>Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations</h2>
        <p>Total net sales and revenue increased by 8 percent year-over-year, driven primarily by strong demand for Services and iPhone product categories across Americas and Europe.</p>
        <p>Item 7. Management's Discussion (page 2 running header)</p>
        <p>Operating income also grew significantly due to gross margin expansion and disciplined operating expense management throughout the fiscal year.</p>

        <h2>Item 8. Financial Statements and Supplementary Data</h2>
        <p>Consolidated statements of operations, comprehensive income, balance sheets, and cash flows for the three years ended September 30, 2025 are presented herein.</p>
    </div>
    </body></html>
    """

    parser = SectionParser()
    result = parser.parse(sample_html)

    assert result.detection_method == "regex_filtered"
    assert "1" in result.items_found
    assert "1A" in result.items_found
    assert "7" in result.items_found
    assert "8" in result.items_found

    item_map = {s.item_number: s for s in result.sections}
    assert "smartphones" in item_map["1"].text
    assert "risks" in item_map["1A"].text
    assert "revenue" in item_map["7"].text or "net sales" in item_map["7"].text
    assert "Consolidated" in item_map["8"].text


def test_section_parser_fallback_single_section():
    # If no Item headers exist, fall back cleanly
    plain_text = "<html><body>This document has no item markers whatsoever. Just raw text describing financial figures.</body></html>"
    parser = SectionParser()
    result = parser.parse(plain_text)

    assert result.detection_method == "fallback_single_section"
    assert len(result.sections) == 1
    assert result.sections[0].item_number == "FULL"
    assert "financial figures" in result.sections[0].text
