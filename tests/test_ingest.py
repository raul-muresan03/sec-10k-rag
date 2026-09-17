from unittest.mock import Mock

import pytest

import etl_pipeline
from etl_pipeline import ingest


def test_download_requires_email(tmp_path, monkeypatch):
    monkeypatch.setenv("SEC_API_EMAIL", "")
    monkeypatch.setattr(etl_pipeline, "DATA_DIR", tmp_path / "data")

    with pytest.raises(RuntimeError, match="SEC_API_EMAIL is missing"):
        ingest.download_10k("NVDA")


def test_download_passes_company_and_data_dir(tmp_path, monkeypatch):
    data_directory = tmp_path / "data"
    monkeypatch.setenv("SEC_API_EMAIL", "analyst@example.com")
    monkeypatch.setattr(etl_pipeline, "DATA_DIR", data_directory)
    downloader_class = Mock(return_value=Mock())
    monkeypatch.setattr(ingest, "Downloader", downloader_class)

    ingest.download_10k("NVDA")

    downloader_class.assert_called_once_with("SEC RAG TOOL", "analyst@example.com", str(data_directory))
    downloader_class.return_value.get.assert_called_once_with("10-K", "NVDA", limit=1)
    assert data_directory.is_dir()
