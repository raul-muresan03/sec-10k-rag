"""Public HTTP shapes for verified filings."""

from pydantic import BaseModel


class FilingSummary(BaseModel):
    filing_id: str
    ticker: str
    company: str
    filing_year: int
    sec_url: str
