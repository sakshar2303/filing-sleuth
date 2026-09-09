import pytest
from backend.crossref.financial_dossier import FinancialDossierEngine

def test_financial_dossier_extraction_and_computations():
    engine = FinancialDossierEngine()
    
    # Mock XBRL CompanyFacts structure
    raw_facts = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "fp": "FY", "fy": 2021, "val": 100_000_000, "accn": "0001-21-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2022, "val": 120_000_000, "accn": "0001-22-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2023, "val": 150_000_000, "accn": "0001-23-01"},
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "fp": "FY", "fy": 2021, "val": 20_000_000, "accn": "0001-21-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2022, "val": 25_000_000, "accn": "0001-22-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2023, "val": 35_000_000, "accn": "0001-23-01"},
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "fp": "FY", "fy": 2021, "val": 25_000_000, "accn": "0001-21-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2022, "val": 30_000_000, "accn": "0001-22-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2023, "val": 42_000_000, "accn": "0001-23-01"},
                        ]
                    }
                },
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "fp": "FY", "fy": 2021, "val": 22_000_000, "accn": "0001-21-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2022, "val": 28_000_000, "accn": "0001-22-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2023, "val": 40_000_000, "accn": "0001-23-01"},
                        ]
                    }
                },
                "Assets": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "fp": "FY", "fy": 2021, "val": 200_000_000, "accn": "0001-21-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2022, "val": 240_000_000, "accn": "0001-22-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2023, "val": 300_000_000, "accn": "0001-23-01"},
                        ]
                    }
                },
                "Liabilities": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "fp": "FY", "fy": 2021, "val": 100_000_000, "accn": "0001-21-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2022, "val": 110_000_000, "accn": "0001-22-01"},
                            {"form": "10-K", "fp": "FY", "fy": 2023, "val": 120_000_000, "accn": "0001-23-01"},
                        ]
                    }
                }
            }
        }
    }

    dossier, facts, computations = engine.extract_dossier("ACME", "Acme Corp", "0000123456", raw_facts)

    assert dossier.company_ticker == "ACME"
    assert dossier.fiscal_years == [2021, 2022, 2023]
    assert len(dossier.series) == 3

    # Check 2023 snapshot
    snap23 = dossier.series[-1]
    assert snap23.fiscal_year == 2023
    assert snap23.revenue == 150_000_000
    assert snap23.net_income == 35_000_000
    assert snap23.operating_margin == 28.0  # 42M / 150M = 28.0%
    assert snap23.net_margin == pytest.approx(23.33, rel=1e-2)
    assert snap23.yoy_revenue_growth_pct == 25.0  # (150 - 120) / 120 = 25.0%
    assert snap23.cash_conversion_pct == pytest.approx(114.3, rel=1e-2)  # 40M / 35M = 114.28%

    # Check Summary KPIs
    kpis = dossier.summary_kpis
    assert kpis["latest_revenue_formatted"] == "$150.00M"
    assert kpis["latest_operating_margin"] == 28.0
    assert kpis["yoy_revenue_growth_pct"] == 25.0
    assert kpis["three_year_cagr_revenue_pct"] == pytest.approx(22.47, rel=1e-2)  # (150/100)^(1/2) - 1 = 22.47%

    # Check extra facts and derivations
    assert len(facts) >= 6
    assert any("Revenue" in (f.xbrl_tag or "") and f.fiscal_year == 2023 for f in facts)
    assert any(c.metric_label == "Operating Margin" for c in computations)
