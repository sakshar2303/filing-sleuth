"""
Unit tests for backend.crossref.alignment.
"""

import pytest
from backend.agent.extraction_agent import ExtractedFact
from backend.crossref.alignment import CrossReferenceAligner, _format_cell_value, _clean_metric_title


def test_format_cell_value():
    assert _format_cell_value(34_550_000_000, "USD") == "$34.55B"
    assert _format_cell_value(120_000_000, "USD") == "$120.00M"
    assert _format_cell_value(50_000, "USD") == "$50.00K"
    assert _format_cell_value(None, "USD") == "N/D"


def test_clean_metric_title():
    assert _clean_metric_title("us-gaap:ResearchAndDevelopmentExpense") == "Research & Development"
    assert _clean_metric_title("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax") == "Total Revenue / Net Sales"
    assert _clean_metric_title("us-gaap:NetIncomeLoss") == "Net Income"


def test_crossref_alignment_and_calendar_mismatch():
    aligner = CrossReferenceAligner()

    f1 = ExtractedFact(
        sub_question_id="sq1",
        company="Apple Inc.",
        cik="0000320193",
        value=34_550_000_000,
        unit="USD",
        fiscal_year=2025,
        period_end="2025-09-27",  # September
        xbrl_tag="us-gaap:ResearchAndDevelopmentExpense",
    )
    f2 = ExtractedFact(
        sub_question_id="sq2",
        company="MICROSOFT CORP",
        cik="0000789019",
        value=32_488_000_000,
        unit="USD",
        fiscal_year=2025,
        period_end="2025-06-30",  # June
        xbrl_tag="us-gaap:ResearchAndDevelopmentExpense",
    )

    matrix = aligner.align([f1, f2])

    assert "Apple Inc." in matrix.companies
    assert "MICROSOFT CORP" in matrix.companies
    assert 2025 in matrix.fiscal_years
    assert len(matrix.rows) >= 1

    # Check cell retrieval
    cell_aapl = matrix.get_cell("Research & Development", "Apple Inc.", 2025)
    assert cell_aapl is not None
    assert cell_aapl.formatted_value == "$34.55B"

    # Check calendar mismatch alert
    assert len(matrix.calendar_warnings) > 0
    assert "Fiscal Year Calendar Mismatch" in matrix.calendar_warnings[0]
    assert "September" in matrix.calendar_warnings[0]
    assert "June" in matrix.calendar_warnings[0]
