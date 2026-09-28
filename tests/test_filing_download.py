from hashlib import sha256

import pytest

from etl_pipeline.filing_download import download_verified
from etl_pipeline.filings import VerifiedFiling


def test_download_publishes_only_verified_bytes_and_reuses_existing(tmp_path, monkeypatch):
    content = (
        b"ACCESSION NUMBER: 0001045810-26-000021\nCONFORMED SUBMISSION TYPE: 10-K\n"
        b"FILED AS OF DATE: 20260225\nfiling body"
    )
    filing = VerifiedFiling(
        "NVDA", 2026, "dev", "0001045810-26-000021", tmp_path / "full-submission.txt",
        sha256(content).hexdigest(),
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021.txt",
    )
    monkeypatch.setenv("SEC_API_EMAIL", "analyst@example.com")
    calls = []

    class Response:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            yield self.body

    def get(url, headers, stream, timeout):
        calls.append((url, headers["User-Agent"]))
        return Response(b"wrong bytes" if len(calls) == 1 else content)

    monkeypatch.setattr("etl_pipeline.filing_download.requests.get", get)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        download_verified(filing)
    assert not filing.path.exists()
    assert not list(tmp_path.glob(".download-*"))

    assert download_verified(filing) == filing.path
    assert filing.path.read_bytes() == content
    assert download_verified(filing) == filing.path
    assert calls == [(filing.sec_url, "SEC RAG Tool analyst@example.com")] * 2


def test_missing_sec_contact_does_not_download(tmp_path, monkeypatch):
    monkeypatch.delenv("SEC_API_EMAIL", raising=False)
    filing = VerifiedFiling("NVDA", 2026, "dev", "0001045810-26-000021", tmp_path / "source", "0" * 64)
    with pytest.raises(ValueError, match="SEC_API_EMAIL"):
        download_verified(filing)
    assert not filing.path.exists()
