"""
Filing Sleuth — SEC Submissions API

Wraps data.sec.gov/submissions/CIK{cik10}.json to retrieve a company's
filing history. This gives us:
  - List of all filings (form type, date, accession number)
  - Primary document filename for each filing
  - Filing dates for time-range filtering

We filter to 10-K (annual) and 10-Q (quarterly) by default, since those
contain the financial data and disclosures this tool targets.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.retrieval.sec_client import SECClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FilingRecord:
    """A single SEC filing entry from the submissions API."""
    accession_number: str     # e.g., "0000320193-23-000106"
    form_type: str            # e.g., "10-K", "10-Q", "10-K/A"
    filing_date: str          # e.g., "2023-11-03"
    primary_document: str     # e.g., "aapl-20230930.htm"
    primary_doc_description: str  # e.g., "10-K"
    reporting_date: str       # e.g., "2023-09-30" (period of report)


@dataclass
class SubmissionsResult:
    """Result from the submissions API for a single company."""
    cik: str
    entity_name: str
    sic: str                          # Standard Industrial Classification code
    state_of_incorporation: str
    fiscal_year_end: str              # e.g., "0930" (MMDD) for September 30
    filings: list[FilingRecord] = field(default_factory=list)


class SubmissionsAPI:
    """Fetch and filter a company's SEC filing history.

    Usage:
        async with SECClient() as client:
            subs = SubmissionsAPI(client)
            result = await subs.get_filings("0000320193", form_types=["10-K"])
            for f in result.filings:
                print(f.accession_number, f.form_type, f.filing_date)
    """

    def __init__(self, client: SECClient) -> None:
        self.client = client

    async def get_filings(
        self,
        cik: str,
        *,
        form_types: list[str] | None = None,
        limit: int = 20,
        include_amendments: bool = False,
    ) -> SubmissionsResult:
        """Get a company's filing history from the SEC submissions API.

        Args:
            cik: 10-digit zero-padded CIK (e.g., "0000320193").
            form_types: Filter to these form types (e.g., ["10-K", "10-Q"]).
                        Defaults to ["10-K", "10-Q"] if None.
            limit: Maximum number of filings to return.
            include_amendments: If True, include amended filings like 10-K/A or 10-Q/A.
                                If False (default), only exact form types are returned
                                unless an amended form type is explicitly in form_types.

        Returns:
            SubmissionsResult with company info and filtered filing list.
        """
        if form_types is None:
            form_types = ["10-K", "10-Q"]

        url = f"{self.client.settings.sec_data_base}/submissions/CIK{cik}.json"
        data = await self.client.get_json(
            url,
            cache_segments=("submissions", f"CIK{cik}"),
        )

        result = SubmissionsResult(
            cik=cik,
            entity_name=data.get("name", ""),
            sic=data.get("sic", ""),
            state_of_incorporation=data.get("stateOfIncorporation", ""),
            fiscal_year_end=data.get("fiscalYearEnd", ""),
        )

        # Parse the recent filings from the inline data
        recent = data.get("filings", {}).get("recent", {})
        if not recent:
            logger.warning("No recent filings found for CIK %s", cik)
            return result

        accession_numbers = recent.get("accessionNumber", [])
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        primary_docs = recent.get("primaryDocument", [])
        primary_doc_descs = recent.get("primaryDocDescription", [])
        reporting_dates = recent.get("reportDate", [])

        # Build FilingRecord list, filtering by form type
        form_types_upper = {ft.upper() for ft in form_types}

        count = 0
        for i in range(len(accession_numbers)):
            form = forms[i] if i < len(forms) else ""
            form_upper = form.upper()
            base_form = form.split("/")[0].upper()

            if include_amendments:
                if base_form not in form_types_upper and form_upper not in form_types_upper:
                    continue
            else:
                if form_upper not in form_types_upper:
                    continue

            record = FilingRecord(
                accession_number=accession_numbers[i],
                form_type=form,
                filing_date=filing_dates[i] if i < len(filing_dates) else "",
                primary_document=primary_docs[i] if i < len(primary_docs) else "",
                primary_doc_description=(
                    primary_doc_descs[i] if i < len(primary_doc_descs) else ""
                ),
                reporting_date=reporting_dates[i] if i < len(reporting_dates) else "",
            )
            result.filings.append(record)
            count += 1
            if count >= limit:
                break

        logger.info(
            "Found %d %s filings for %s (%s)",
            len(result.filings),
            "/".join(form_types),
            result.entity_name,
            cik,
        )
        return result

    async def get_recent_annual_filings(
        self,
        cik: str,
        count: int = 3,
        include_amendments: bool = False,
    ) -> list[FilingRecord]:
        """Convenience: get the N most recent 10-K filings for a company."""
        result = await self.get_filings(
            cik,
            form_types=["10-K"],
            limit=count,
            include_amendments=include_amendments,
        )
        return result.filings

    async def get_recent_quarterly_filings(
        self,
        cik: str,
        count: int = 4,
        include_amendments: bool = False,
    ) -> list[FilingRecord]:
        """Convenience: get the N most recent 10-Q filings for a company."""
        result = await self.get_filings(
            cik,
            form_types=["10-Q"],
            limit=count,
            include_amendments=include_amendments,
        )
        return result.filings

