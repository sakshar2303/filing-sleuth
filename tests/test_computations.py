"""
Unit tests for backend.crossref.computations.
"""

import pytest
from backend.agent.extraction_agent import ExtractedFact
from backend.crossref.computations import FinancialComputations


def test_margin_calculations():
    computer = FinancialComputations()

    f_rd = ExtractedFact(
        sub_question_id="sq1",
        company="Apple Inc.",
        cik="0000320193",
        value=34_550_000_000,
        unit="USD",
        fiscal_year=2025,
        xbrl_tag="us-gaap:ResearchAndDevelopmentExpense",
    )
    f_rev = ExtractedFact(
        sub_question_id="sq2",
        company="Apple Inc.",
        cik="0000320193",
        value=416_161_000_000,
        unit="USD",
        fiscal_year=2025,
        xbrl_tag="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    )

    results = computer.compute_margins([f_rd, f_rev])
    assert len(results) == 1
    res = results[0]
    assert res.computation_type == "MARGIN_RATIO"
    assert res.company == "Apple Inc."
    assert res.fiscal_year == 2025
    assert res.result_value == 8.30
    assert res.result_formatted == "8.30%"
    assert "8.30%" in res.description


def test_yoy_growth_calculations():
    computer = FinancialComputations()

    f_2025 = ExtractedFact(
        sub_question_id="sq1",
        company="Apple Inc.",
        cik="0000320193",
        value=34_550_000_000,
        unit="USD",
        fiscal_year=2025,
        xbrl_tag="us-gaap:ResearchAndDevelopmentExpense",
    )
    f_2024 = ExtractedFact(
        sub_question_id="sq2",
        company="Apple Inc.",
        cik="0000320193",
        value=31_370_000_000,
        unit="USD",
        fiscal_year=2024,
        xbrl_tag="us-gaap:ResearchAndDevelopmentExpense",
    )

    results = computer.compute_yoy_growth([f_2025, f_2024])
    assert len(results) == 1
    res = results[0]
    assert res.computation_type == "YOY_GROWTH"
    assert res.fiscal_year == 2025
    # (34550 - 31370) / 31370 = 10.14%
    assert res.result_value == 10.14
    assert res.result_formatted == "+10.14%"


def test_peer_spread_calculations():
    computer = FinancialComputations()

    from backend.crossref.computations import ComputedResult
    r1 = ComputedResult(
        computation_type="MARGIN_RATIO",
        metric_label="R&D as % of Revenue",
        company="Apple Inc.",
        fiscal_year=2025,
        result_value=8.30,
        result_formatted="8.30%",
        formula="",
        inputs=[],
        description="",
    )
    r2 = ComputedResult(
        computation_type="MARGIN_RATIO",
        metric_label="R&D as % of Revenue",
        company="MICROSOFT CORP",
        fiscal_year=2025,
        result_value=11.53,
        result_formatted="11.53%",
        formula="",
        inputs=[],
        description="",
    )

    spreads = computer.compute_peer_spreads([r1, r2])
    assert len(spreads) == 1
    spread = spreads[0]
    assert spread.computation_type == "PEER_SPREAD"
    # 8.30 - 11.53 = -3.23%
    assert spread.result_value == -3.23
