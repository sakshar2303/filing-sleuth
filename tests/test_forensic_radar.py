import pytest
from backend.agent.extraction_agent import ExtractedFact
from backend.crossref.forensic_radar import ForensicRadarEngine, ForensicScorecard

def test_pristine_company_evaluation():
    engine = ForensicRadarEngine()
    facts = [
        ExtractedFact(
            sub_question_id="sq1",
            company="AAPL",
            cik="0000320193",
            fiscal_year=2023,
            metric="Revenue",
            value=383285000000.0,
            xbrl_tag="RevenueFromContractWithCustomerExcludingAssessedTax",
            status="FOUND",
            source_type="XBRL",
        ),
        ExtractedFact(
            sub_question_id="sq2",
            company="AAPL",
            cik="0000320193",
            fiscal_year=2023,
            metric="Net Income",
            value=96995000000.0,
            xbrl_tag="NetIncomeLoss",
            status="FOUND",
            source_type="XBRL",
        ),
        ExtractedFact(
            sub_question_id="sq3",
            company="AAPL",
            cik="0000320193",
            fiscal_year=2023,
            metric="Operating Cash Flow",
            value=110543000000.0, # OCF > Net Income (Pristine quality!)
            xbrl_tag="NetCashProvidedByUsedInOperatingActivities",
            status="FOUND",
            source_type="XBRL",
        ),
        ExtractedFact(
            sub_question_id="sq4",
            company="AAPL",
            cik="0000320193",
            fiscal_year=2023,
            metric="Accounts Receivable",
            value=29508000000.0, # ~28 days DSO
            xbrl_tag="AccountsReceivableNetCurrent",
            status="FOUND",
            source_type="XBRL",
        ),
        ExtractedFact(
            sub_question_id="sq5",
            company="AAPL",
            cik="0000320193",
            fiscal_year=2023,
            metric="Total Assets",
            value=352583000000.0,
            xbrl_tag="Assets",
            status="FOUND",
            source_type="XBRL",
        ),
        ExtractedFact(
            sub_question_id="sq6",
            company="AAPL",
            cik="0000320193",
            fiscal_year=2023,
            metric="Total Liabilities",
            value=290437000000.0,
            xbrl_tag="Liabilities",
            status="FOUND",
            source_type="XBRL",
        ),
    ]

    scorecard = engine.evaluate_company("AAPL", facts, fiscal_year=2023)
    assert scorecard is not None
    assert scorecard.company == "AAPL"
    assert scorecard.fiscal_year == 2023
    assert scorecard.overall_score >= 75
    assert len(scorecard.metrics) == 3
    
    # Check Accrual Gap metric
    accrual_metric = next(m for m in scorecard.metrics if m.metric_id == "ACCRUAL_GAP")
    assert accrual_metric.status == "PASS"
    assert "Cash > Net Income" in accrual_metric.display_value

    # Check DSO metric
    dso_metric = next(m for m in scorecard.metrics if m.metric_id == "DSO")
    assert dso_metric.status == "PASS"
    assert "28." in dso_metric.display_value


def test_high_risk_company_evaluation():
    engine = ForensicRadarEngine()
    # Company with high net income but tiny operating cash flow and high DSO
    facts = [
        ExtractedFact(
            sub_question_id="sq1",
            company="SUSP",
            cik="0000000001",
            fiscal_year=2023,
            metric="Revenue",
            value=1000000000.0,
            xbrl_tag="RevenueFromContractWithCustomerExcludingAssessedTax",
            status="FOUND",
            source_type="XBRL",
        ),
        ExtractedFact(
            sub_question_id="sq2",
            company="SUSP",
            cik="0000000001",
            fiscal_year=2023,
            metric="Net Income",
            value=350000000.0, # $350M Net Income
            xbrl_tag="NetIncomeLoss",
            status="FOUND",
            source_type="XBRL",
        ),
        ExtractedFact(
            sub_question_id="sq3",
            company="SUSP",
            cik="0000000001",
            fiscal_year=2023,
            metric="Operating Cash Flow",
            value=20000000.0, # Only $20M cash flow! ($330M accrual gap!)
            xbrl_tag="NetCashProvidedByUsedInOperatingActivities",
            status="FOUND",
            source_type="XBRL",
        ),
        ExtractedFact(
            sub_question_id="sq4",
            company="SUSP",
            cik="0000000001",
            fiscal_year=2023,
            metric="Accounts Receivable",
            value=450000000.0, # 164 days DSO! Severe channel stuffing!
            xbrl_tag="AccountsReceivableNetCurrent",
            status="FOUND",
            source_type="XBRL",
        ),
        ExtractedFact(
            sub_question_id="sq5",
            company="SUSP",
            cik="0000000001",
            fiscal_year=2023,
            metric="Total Assets",
            value=1200000000.0,
            xbrl_tag="Assets",
            status="FOUND",
            source_type="XBRL",
        ),
    ]

    scorecard = engine.evaluate_company("SUSP", facts, fiscal_year=2023)
    assert scorecard is not None
    assert scorecard.overall_score < 65
    assert scorecard.risk_level in ["GRAY_ZONE", "HIGH_RISK"]
    assert len(scorecard.red_flags) >= 2
