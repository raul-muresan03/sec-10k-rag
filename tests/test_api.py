from fastapi.testclient import TestClient

from api.main import create_app
from etl_pipeline.filing_store import PreparedFiling


def test_health_reports_live_process():
    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_filings_lists_only_prepared_filing_identities(tmp_path):
    filing = PreparedFiling(
        filing_id="1045810-0001045810-26-000021", ticker="NVDA", year=2026,
        accession="0001045810-26-000021",
        sec_url="https://www.sec.gov/Archives/edgar/data/1045810/example.txt",
        index_version="a" * 64, index_path=tmp_path / "index.json", index_sha256="b" * 64,
        chunk_count=2,
    )

    class Catalog:
        def prepared(self):
            return [filing]

    with TestClient(create_app(store=Catalog())) as client:
        response = client.get("/api/filings")

    assert response.status_code == 200
    assert response.json() == [{
        "filing_id": filing.filing_id, "ticker": "NVDA", "company": "NVIDIA",
        "filing_year": 2026, "sec_url": filing.sec_url,
    }]
