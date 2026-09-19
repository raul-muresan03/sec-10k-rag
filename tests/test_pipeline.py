from unittest.mock import Mock

import pytest

import etl_pipeline
from etl_pipeline import pipeline


def make_filing(data_directory):
    path = data_directory / "sec-edgar-filings/NVDA/10-K/accession/full-submission.txt"
    path.parent.mkdir(parents=True)
    path.write_text("raw submission")
    return path


def test_ensure_index_runs_pipeline_and_records_accession(data_directory, monkeypatch):
    filing_path = make_filing(data_directory)
    download = Mock(return_value=filing_path)
    parse = Mock()
    clean = Mock()

    def create_vector_store(_):
        (data_directory / pipeline.VECTOR_STORE_FILENAME).write_text("{}")

    chunk = Mock(side_effect=create_vector_store)
    monkeypatch.setattr(pipeline, "download_10k", download)
    monkeypatch.setattr(pipeline, "parse_10K", parse)
    monkeypatch.setattr(pipeline, "clean_10K", clean)
    monkeypatch.setattr(pipeline, "chunk_10K", chunk)

    pipeline.ensure_index("nvda", year=2026)

    download.assert_called_once_with("nvda", 2026)
    parse.assert_called_once_with(str(filing_path))
    clean.assert_called_once_with(str(data_directory / "output_parser.txt"))
    chunk.assert_called_once_with(str(data_directory / "output_cleaner.txt"))
    accession = (data_directory / pipeline.ACTIVE_ACCESSION_FILENAME).read_text()
    assert accession == "accession"


def test_ensure_index_checks_sec_then_reuses_matching_index(data_directory, monkeypatch):
    filing_path = make_filing(data_directory)
    (data_directory / pipeline.VECTOR_STORE_FILENAME).write_text("{}")
    (data_directory / pipeline.ACTIVE_ACCESSION_FILENAME).write_text("accession")
    download = Mock(return_value=filing_path)
    parse = Mock()
    monkeypatch.setattr(pipeline, "download_10k", download)
    monkeypatch.setattr(pipeline, "parse_10K", parse)

    pipeline.ensure_index("NVDA", 2026)

    download.assert_called_once_with("NVDA", 2026)
    parse.assert_not_called()


def test_ensure_index_requires_vector_store_after_chunking(data_directory, monkeypatch):
    filing_path = make_filing(data_directory)
    vector_store_path = data_directory / pipeline.VECTOR_STORE_FILENAME
    accession_path = data_directory / pipeline.ACTIVE_ACCESSION_FILENAME
    vector_store_path.write_text("old vectors")
    accession_path.write_text("old-accession")
    monkeypatch.setattr(pipeline, "download_10k", Mock(return_value=filing_path))
    monkeypatch.setattr(pipeline, "parse_10K", Mock())
    monkeypatch.setattr(pipeline, "clean_10K", Mock())
    monkeypatch.setattr(pipeline, "chunk_10K", Mock())

    with pytest.raises(RuntimeError, match="Vector store was not created"):
        pipeline.ensure_index("NVDA", 2026)

    assert not accession_path.exists()
    assert not vector_store_path.exists()
