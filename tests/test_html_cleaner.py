"""
Unit tests for backend.parsing.html_cleaner.
"""

import pytest
from backend.parsing.html_cleaner import (
    clean_html,
    clean_html_preserve_structure,
    extract_text_from_element,
)
from bs4 import BeautifulSoup



def test_clean_html_basic():
    html = """
    <html>
    <head><style>.test { color: red; }</style><script>alert(1);</script></head>
    <body>
        <h1>Title Header</h1>
        <p>This is a <b>financial</b> paragraph with &nbsp; entities &#160; and extra   spaces.</p>
    </body>
    </html>
    """
    cleaned = clean_html(html)
    assert "alert" not in cleaned
    assert ".test" not in cleaned
    assert "Title Header" in cleaned
    assert "financial" in cleaned
    assert "paragraph with entities and extra spaces." in cleaned


def test_clean_html_table_preservation():
    html = """
    <table>
        <tr><th>Metric</th><th>2024</th><th>2025</th></tr>
        <tr><td>Revenue</td><td>$100M</td><td>$120M</td></tr>
    </table>
    """
    cleaned = clean_html(html)
    assert "Metric" in cleaned
    assert "Revenue" in cleaned
    assert "$100M" in cleaned
    assert "$120M" in cleaned


def test_clean_html_empty_input():
    assert clean_html("") == ""
    assert clean_html("   ") == ""


def test_clean_html_preserve_structure():
    html = "<div><p>First paragraph.</p><p>Second paragraph.</p></div>"
    soup = clean_html_preserve_structure(html)
    assert isinstance(soup, BeautifulSoup)
    p_tags = soup.find_all("p")
    assert len(p_tags) == 2


def test_extract_text_from_element():
    html = "<div><span>Nested <b>Content</b></span></div>"
    soup = BeautifulSoup(html, "html.parser")
    text = extract_text_from_element(soup.div)
    assert "Nested" in text and "Content" in text

