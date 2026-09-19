from datetime import date
from unittest.mock import Mock

import pytest

import etl_pipeline
from etl_pipeline import ingest


def write_filing(data_directory, ticker, accession, filed_on):
    path = (
        data_directory
        / "sec-edgar-filings"
        / ticker
        / "10-K"
        / accession
        / "full-submission.txt"
    )
    path.parent.mkdir(parents=True)
    path.write_text(f"FILED AS OF DATE: {filed_on}\n")
    return path


def test_download_requires_email(tmp_path, monkeypatch):
    monkeypatch.setenv("SEC_API_EMAIL", "")
    monkeypatch.setattr(etl_pipeline, "DATA_DIR", tmp_path / "data")

    with pytest.raises(RuntimeError, match="SEC_API_EMAIL is missing"):
        ingest.download_10k("NVDA", 2026)


def test_download_returns_latest_filing(data_directory, monkeypatch):
    older = write_filing(data_directory, "NVDA", "older-accession", "20250226")
    latest = write_filing(data_directory, "NVDA", "latest-accession", "20260225")
    monkeypatch.setenv("SEC_API_EMAIL", "analyst@example.com")
    downloader_class = Mock(return_value=Mock())
    downloader_class.return_value.get.return_value = 1
    monkeypatch.setattr(ingest, "Downloader", downloader_class)

    filing_path = ingest.download_10k(" nvda ", 2026)

    downloader_class.assert_called_once_with("SEC RAG TOOL", "analyst@example.com", str(data_directory))
    downloader_class.return_value.get.assert_called_once_with(
        "10-K",
        "NVDA",
        limit=1,
        after="2026-01-01",
        before=date.today().isoformat(),
    )
    assert filing_path == latest
    assert older.is_file()


def test_download_filters_by_filing_year(data_directory, monkeypatch):
    selected = write_filing(data_directory, "AAPL", "2025-accession", "20251031")
    write_filing(data_directory, "AAPL", "2024-accession", "20241101")
    monkeypatch.setenv("SEC_API_EMAIL", "analyst@example.com")
    downloader_class = Mock(return_value=Mock())
    downloader_class.return_value.get.return_value = 1
    monkeypatch.setattr(ingest, "Downloader", downloader_class)

    filing_path = ingest.download_10k("aapl", year=2025)

    downloader_class.return_value.get.assert_called_once_with(
        "10-K",
        "AAPL",
        limit=1,
        after="2025-01-01",
        before="2025-12-31",
    )
    assert filing_path == selected


@pytest.mark.parametrize("year", [1993, date.today().year + 1])
def test_download_rejects_year_outside_edgar_range(year):
    with pytest.raises(ValueError, match="year must be between"):
        ingest.download_10k("NVDA", year=year)


def test_download_stops_when_sec_returns_no_filing(data_directory, monkeypatch):
    monkeypatch.setenv("SEC_API_EMAIL", "analyst@example.com")
    downloader_class = Mock(return_value=Mock())
    downloader_class.return_value.get.return_value = 0
    monkeypatch.setattr(ingest, "Downloader", downloader_class)

    with pytest.raises(RuntimeError, match="SEC returned no 10-K filing"):
        ingest.download_10k("NVDA", year=2025)


def test_download_wraps_downloader_initialization_failure(data_directory, monkeypatch):
    monkeypatch.setenv("SEC_API_EMAIL", "analyst@example.com")
    monkeypatch.setattr(ingest, "Downloader", Mock(side_effect=OSError("SEC unavailable")))

    with pytest.raises(RuntimeError, match="SEC download failed for NVDA"):
        ingest.download_10k("NVDA", 2026)


def test_download_stops_for_malformed_cached_filing(data_directory, monkeypatch):
    malformed = (
        data_directory
        / "sec-edgar-filings"
        / "NVDA"
        / "10-K"
        / "malformed"
        / "full-submission.txt"
    )
    malformed.parent.mkdir(parents=True)
    malformed.write_text("missing filing date")
    write_filing(data_directory, "NVDA", "valid", "20250226")
    monkeypatch.setenv("SEC_API_EMAIL", "analyst@example.com")
    downloader_class = Mock(return_value=Mock())
    downloader_class.return_value.get.return_value = 1
    monkeypatch.setattr(ingest, "Downloader", downloader_class)

    with pytest.raises(RuntimeError, match="Filing date not found"):
        ingest.download_10k("NVDA", year=2025)
