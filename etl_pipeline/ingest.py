from datetime import date
import os
from pathlib import Path
import re

from dotenv import load_dotenv
from sec_edgar_downloader import Downloader

import etl_pipeline

load_dotenv()

EARLIEST_EDGAR_YEAR = 1994
FILING_DATE_PATTERN = re.compile(r"FILED AS OF DATE:\s*(\d{8})")


def _read_filing_date(path: Path) -> date:
    with path.open("r", errors="replace") as filing:
        header = filing.read(16_384)

    match = FILING_DATE_PATTERN.search(header)
    if match is None:
        raise RuntimeError(f"Filing date not found in {path}")

    try:
        return date.fromisoformat(
            f"{match.group(1)[:4]}-{match.group(1)[4:6]}-{match.group(1)[6:]}"
        )
    except ValueError as error:
        raise RuntimeError(f"Invalid filing date in {path}") from error


def _find_latest_filing(ticker: str, year: int) -> Path:
    filing_root = etl_pipeline.DATA_DIR / "sec-edgar-filings" / ticker / "10-K"
    filings = []
    for path in filing_root.glob("*/full-submission.txt"):
        filing_date = _read_filing_date(path)
        if filing_date.year == year:
            filings.append((filing_date, path))

    if not filings:
        raise RuntimeError(f"No 10-K filing found for {ticker} filed in {year}")

    return max(filings, key=lambda filing: filing[0])[1]


def download_10k(company_code: str, year: int) -> Path:
    ticker = company_code.strip().upper()
    current_year = date.today().year
    if not EARLIEST_EDGAR_YEAR <= year <= current_year:
        raise ValueError(f"year must be between {EARLIEST_EDGAR_YEAR} and {current_year}")

    email = os.getenv("SEC_API_EMAIL")
    if not email:
        raise RuntimeError("SEC_API_EMAIL is missing from .env file")

    etl_pipeline.DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        downloader = Downloader("SEC RAG TOOL", email, str(etl_pipeline.DATA_DIR))
        last_day = min(date(year, 12, 31), date.today())
        downloaded = downloader.get(
            "10-K",
            ticker,
            limit=1,
            after=f"{year}-01-01",
            before=last_day.isoformat(),
        )
    except Exception as error:
        raise RuntimeError(f"SEC download failed for {ticker}") from error

    if downloaded == 0:
        raise RuntimeError(f"SEC returned no 10-K filing for {ticker} in {year}")

    return _find_latest_filing(ticker, year)

if __name__ == "__main__":
    download_10k("NVDA", 2026)
