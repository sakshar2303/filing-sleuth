"""
Unit tests for backend.agent.synthesis_agent.
"""

import pytest
from backend.agent.extraction_agent import ExtractedFact
from backend.agent.query_planner import ExecutionPlan, PlannedCompany, TimeRange
from backend.agent.synthesis_agent import SynthesisAgent


@pytest.mark.asyncio
async def test_synthesis_agent_report_generation():
    agent = SynthesisAgent()

    plan = ExecutionPlan(
        original_question="What was Apple's R&D spend in FY2025?",
        companies=[PlannedCompany(ticker="AAPL", name="Apple Inc.", cik="0000320193")],
        time_range=TimeRange(type="ANNUAL", count=1),
    )

    facts = [
        ExtractedFact(
            sub_question_id="sq1",
            status="FOUND",
            claim="Apple Inc.'s R&D expense for FY2025 was $34.55B.",
            value=34_550_000_000,
            unit="USD",
            fiscal_year=2025,
            fiscal_label="FY2025",
            company="Apple Inc.",
            cik="0000320193",
            accession_number="0000320193-25-000079",
            source_type="XBRL",
            xbrl_tag="us-gaap:ResearchAndDevelopmentExpense",
            item_section="Item 8: Financial Statements",
        ),
        ExtractedFact(
            sub_question_id="sq2",
            status="FOUND",
            claim="Apple Inc.'s Revenue for FY2025 was $416.16B.",
            value=416_161_000_000,
            unit="USD",
            fiscal_year=2025,
            fiscal_label="FY2025",
            company="Apple Inc.",
            cik="0000320193",
            accession_number="0000320193-25-000079",
            source_type="XBRL",
            xbrl_tag="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            item_section="Item 8: Financial Statements",
        ),
    ]

    report = await agent.synthesize("What was Apple's R&D spend in FY2025?", plan, facts)

    assert report.executive_summary != ""
    assert report.comparison_table_markdown != ""
    assert len(report.citations) == 2
    assert report.citations[0].citation_id == "[1]"
    assert report.citations[0].accession_number == "0000320193-25-000079"
    assert len(report.key_findings) >= 2
