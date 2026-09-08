"""
Unit tests for backend.agent.query_planner.
"""

import pytest
from backend.agent.query_planner import QueryPlanner


@pytest.mark.asyncio
async def test_planner_single_metric():
    planner = QueryPlanner()
    plan = await planner.plan("What was Apple's revenue for the latest fiscal year?")

    assert len(plan.companies) == 1
    assert plan.companies[0].ticker == "AAPL"
    assert plan.intent in ["SINGLE_METRIC", "TREND"]
    assert len(plan.sub_questions) >= 1
    sq = plan.sub_questions[0]
    assert sq.company_ticker == "AAPL"
    assert sq.source_preference == "XBRL"


@pytest.mark.asyncio
async def test_planner_comparative_trend():
    planner = QueryPlanner()
    plan = await planner.plan("Compare R&D spend as % of revenue between Apple and Microsoft over the last 3 years")

    assert len(plan.companies) >= 2
    tickers = {c.ticker for c in plan.companies}
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    assert plan.intent == "COMPARATIVE_TREND"
    assert plan.requires_computation is True
    # Should have separate sub-questions for each company and year
    assert len(plan.sub_questions) >= 6


@pytest.mark.asyncio
async def test_planner_qualitative_litigation():
    planner = QueryPlanner()
    plan = await planner.plan("What legal proceedings or lawsuits did Tesla disclose in its recent filing?")

    assert len(plan.companies) == 1
    assert plan.companies[0].ticker == "TSLA"
    assert plan.intent == "QUALITATIVE_DISCLOSURE"
    sq = plan.sub_questions[0]
    assert sq.source_preference == "TEXT"
    assert sq.target_item == "3"
