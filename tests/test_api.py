from fastapi.testclient import TestClient

from api.main import create_app
from etl_pipeline.filing_store import PreparedFiling
from etl_pipeline.filings import VerifiedFiling


def test_health_reports_live_process():
    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_filings_lists_prepared_and_unprepared_filing_identities(tmp_path):
    filing = PreparedFiling(
        filing_id="1045810-0001045810-26-000021", ticker="NVDA", year=2026,
        accession="0001045810-26-000021",
        sec_url="https://www.sec.gov/Archives/edgar/data/1045810/example.txt",
        index_version="a" * 64, index_path=tmp_path / "index.json", index_sha256="b" * 64,
        chunk_count=2,
    )

    class Catalog:
        def catalog(self):
            return {
                filing.filing_id: VerifiedFiling(
                    "NVDA", 2026, "dev", filing.accession, tmp_path / "nvda", "a" * 64, filing.sec_url,
                ),
                "other": VerifiedFiling("AMZN", 2021, "dev", "0001018724-21-000004", tmp_path / "amzn",
                                        "b" * 64, "https://www.sec.gov/other"),
            }

        def prepared(self):
            return [filing]

    with TestClient(create_app(store=Catalog())) as client:
        response = client.get("/api/filings")

    assert response.status_code == 200
    assert response.json() == [{
        "filing_id": filing.filing_id, "ticker": "NVDA", "company": "NVIDIA",
        "filing_year": 2026, "sec_url": filing.sec_url, "status": "ready", "detail": None,
    }, {
        "filing_id": "other", "ticker": "AMZN", "company": "Amazon", "filing_year": 2021,
        "sec_url": "https://www.sec.gov/other", "status": "unprepared", "detail": None,
    }]
