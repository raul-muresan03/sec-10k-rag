from threading import Event

from fastapi.testclient import TestClient

from api.main import create_app
from etl_pipeline.filings import VerifiedFiling


def test_prepare_is_idempotent_and_exposes_progress_then_ready(tmp_path, monkeypatch):
    filing_id = "1045810-0001045810-26-000021"
    filing = VerifiedFiling(
        "NVDA", 2026, "dev", "0001045810-26-000021", tmp_path / "source", "a" * 64,
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021.txt",
    )
    started, release = Event(), Event()

    class Catalog:
        ready = False
        builds = 0

        def catalog(self):
            return {filing_id: filing}

        def prepared(self):
            return [type("Ready", (), {"filing_id": filing_id})()] if self.ready else []

        def prepare_selected(self, ticker, year):
            self.builds += 1
            self.ready = True

    store = Catalog()

    def download(_):
        started.set()
        assert release.wait(5)

    monkeypatch.setattr("api.preparation.download_verified", download)
    monkeypatch.setattr("api.preparation.PreparationService._wait_for_model", lambda self: None)
    try:
        with TestClient(create_app(store=store)) as client:
            assert client.get("/api/filings").json()[0]["status"] == "unprepared"
            assert client.post("/api/filings/unknown/prepare").status_code == 404
            assert client.post(f"/api/filings/{filing_id}/prepare").status_code == 202
            assert started.wait(5)
            assert client.get("/api/filings").json()[0]["status"] == "downloading"
            assert client.post(f"/api/filings/{filing_id}/prepare").json()["status"] == "downloading"
            release.set()
            for _ in range(100):
                if client.get("/api/filings").json()[0]["status"] == "ready":
                    break
            else:
                raise AssertionError("filing never became ready")
            assert store.builds == 1
            assert client.post(f"/api/filings/{filing_id}/prepare").json()["status"] == "ready"
    finally:
        release.set()


def test_failed_preparation_can_be_retried(tmp_path, monkeypatch):
    filing_id = "1045810-0001045810-26-000021"
    filing = VerifiedFiling("NVDA", 2026, "dev", "0001045810-26-000021", tmp_path / "source", "a" * 64)

    class Catalog:
        def catalog(self):
            return {filing_id: filing}

        def prepared(self):
            return []

    attempts = []

    def fail(_):
        attempts.append(1)
        raise ValueError("SEC returned a SHA-256 mismatch")

    monkeypatch.setattr("api.preparation.download_verified", fail)
    with TestClient(create_app(store=Catalog())) as client:
        for expected in (1, 2):
            client.post(f"/api/filings/{filing_id}/prepare")
            for _ in range(100):
                status = client.get("/api/filings").json()[0]
                if status["status"] == "failed":
                    break
            assert status["status"] == "failed"
            assert "SHA-256" in status["detail"]
            assert len(attempts) == expected


def test_catalog_is_available_while_models_download(tmp_path):
    filing = VerifiedFiling("NVDA", 2026, "dev", "0001045810-26-000021", tmp_path / "source", "a" * 64)

    class Catalog:
        def catalog(self):
            return {"known": filing}

        def prepared(self):
            raise RuntimeError("Ollama embedding model not installed")

    with TestClient(create_app(store=Catalog())) as client:
        response = client.get("/api/filings")
    assert response.status_code == 200
    assert response.json()[0]["status"] == "unprepared"
