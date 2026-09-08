"""
Filing Sleuth — Unit Tests for XBRL Facts API

Tests the XBRL data extraction logic using mocked CompanyFacts responses.
"""

import pytest
from unittest.mock import AsyncMock

from backend.retrieval.xbrl_facts import XBRLFactsAPI
from backend.retrieval.sec_client import SECClient


# Mock XBRL response matching SEC's actual structure (simplified)
MOCK_XBRL_RESPONSE = {
    "cik": 320193,
    "entityName": "Apple Inc.",
    "facts": {
        "dei": {
            "EntityCommonStockSharesOutstanding": {
                "label": "Entity Common Stock, Shares Outstanding",
                "description": "...",
                "units": {
                    "shares": [
                        {
                            "end": "2023-10-20",
                            "val": 15552752000,
                            "accn": "0000320193-23-000106",
                            "fy": 2023,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2023-11-03",
                            "frame": "CY2023Q3I",
                        }
                    ]
                },
            }
        },
        "us-gaap": {
            "Revenues": {
                "label": "Revenues",
                "description": "...",
                "units": {
                    "USD": [
                        {
                            "start": "2022-09-25",
                            "end": "2023-09-30",
                            "val": 383285000000,
                            "accn": "0000320193-23-000106",
                            "fy": 2023,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2023-11-03",
                            "frame": "CY2023",
                        },
                        {
                            "start": "2021-09-26",
                            "end": "2022-09-24",
                            "val": 394328000000,
                            "accn": "0000320193-22-000108",
                            "fy": 2022,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2022-10-28",
                            "frame": "CY2022",
                        },
                        {
                            "start": "2023-10-01",
                            "end": "2023-12-30",
                            "val": 119575000000,
                            "accn": "0000320193-24-000006",
                            "fy": 2024,
                            "fp": "Q1",
                            "form": "10-Q",
                            "filed": "2024-02-02",
                            "frame": "CY2023Q4",
                        },
                    ]
                },
            },
            "ResearchAndDevelopmentExpense": {
                "label": "Research and Development Expense",
                "description": "...",
                "units": {
                    "USD": [
                        {
                            "start": "2022-09-25",
                            "end": "2023-09-30",
                            "val": 29915000000,
                            "accn": "0000320193-23-000106",
                            "fy": 2023,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2023-11-03",
                            "frame": "CY2023",
                        },
                        {
                            "start": "2021-09-26",
                            "end": "2022-09-24",
                            "val": 26251000000,
                            "accn": "0000320193-22-000108",
                            "fy": 2022,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2022-10-28",
                            "frame": "CY2022",
                        },
                    ]
                },
            },
        },
    },
}


class TestXBRLFactsAPI:
    @pytest.fixture
    async def xbrl_api(self):
        client = AsyncMock(spec=SECClient)
        client.settings = AsyncMock()
        client.settings.sec_data_base = "https://data.sec.gov"
        client.get_json = AsyncMock(return_value=MOCK_XBRL_RESPONSE)
        return XBRLFactsAPI(client)

    @pytest.mark.asyncio
    async def test_get_facts_direct_concept(self, xbrl_api):
        facts = await xbrl_api.get_facts("0000320193", "Revenues")
        assert len(facts) > 0
        # Should find all revenue entries
        fy_facts = [f for f in facts if f.fiscal_period == "FY"]
        assert len(fy_facts) == 2  # FY2023 and FY2022

    @pytest.mark.asyncio
    async def test_get_facts_filter_form_type(self, xbrl_api):
        facts = await xbrl_api.get_facts(
            "0000320193", "Revenues", form_types=["10-K"]
        )
        for f in facts:
            assert f.form_type == "10-K"

    @pytest.mark.asyncio
    async def test_get_facts_filter_period(self, xbrl_api):
        facts = await xbrl_api.get_facts(
            "0000320193", "Revenues", fiscal_periods=["FY"]
        )
        for f in facts:
            assert f.fiscal_period == "FY"

    @pytest.mark.asyncio
    async def test_get_facts_by_common_name_revenue(self, xbrl_api):
        facts = await xbrl_api.get_facts_by_common_name("0000320193", "revenue")
        assert len(facts) > 0
        assert facts[0].concept == "Revenues"

    @pytest.mark.asyncio
    async def test_get_facts_by_common_name_rd(self, xbrl_api):
        facts = await xbrl_api.get_facts_by_common_name(
            "0000320193", "research_and_development"
        )
        assert len(facts) > 0
        assert facts[0].concept == "ResearchAndDevelopmentExpense"

    @pytest.mark.asyncio
    async def test_get_annual_metric(self, xbrl_api):
        facts = await xbrl_api.get_annual_metric(
            "0000320193", "revenue", latest_n=2
        )
        assert len(facts) == 2
        # Should be sorted by fiscal year descending
        assert facts[0].fiscal_year >= facts[1].fiscal_year

    @pytest.mark.asyncio
    async def test_get_facts_nonexistent_concept(self, xbrl_api):
        facts = await xbrl_api.get_facts(
            "0000320193", "NonExistentConcept12345"
        )
        assert len(facts) == 0

    @pytest.mark.asyncio
    async def test_fact_values_correct(self, xbrl_api):
        facts = await xbrl_api.get_facts(
            "0000320193", "Revenues",
            form_types=["10-K"],
            fiscal_periods=["FY"],
        )
        fy2023 = [f for f in facts if f.fiscal_year == 2023]
        assert len(fy2023) == 1
        assert fy2023[0].value == 383285000000  # $383.285B
        assert fy2023[0].unit == "USD"
        assert fy2023[0].accession_number == "0000320193-23-000106"

    @pytest.mark.asyncio
    async def test_fact_period_data(self, xbrl_api):
        facts = await xbrl_api.get_facts(
            "0000320193", "Revenues",
            form_types=["10-K"],
            fiscal_periods=["FY"],
        )
        fy2023 = [f for f in facts if f.fiscal_year == 2023][0]
        assert fy2023.period_start == "2022-09-25"
        assert fy2023.period_end == "2023-09-30"
        assert fy2023.frame == "CY2023"
