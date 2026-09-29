from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.preparation import PreparationService
from api.settings import Settings
from etl_pipeline.filings import VerifiedFiling


def test_operator_mode_lists_ready_filings_and_refuses_prepare(tmp_path, monkeypatch):
    ready = VerifiedFiling("NVDA", 2026, "dev", "0001045810-26-000021", tmp_path / "ready", "a" * 64)
    pending = VerifiedFiling("F", 2014, "dev", "0000037996-14-000010", tmp_path / "pending", "b" * 64)

    class Catalog:
        def catalog(self):
            return {"ready-id": ready, "pending-id": pending}

        def prepared(self):
            return [SimpleNamespace(filing_id="ready-id")]

    def must_not_prepare(self, filing_id):
        pytest.fail(f"Unexpected public preparation for {filing_id}")

    monkeypatch.setattr(PreparationService, "start", must_not_prepare)
    with TestClient(create_app(store=Catalog(), settings=Settings(preparation_access="operator"))) as client:
        response = client.get("/api/filings")
        assert response.status_code == 200
        assert [(filing["filing_id"], filing["status"]) for filing in response.json()] == [("ready-id", "ready")]
        for filing_id in ("ready-id", "pending-id", "unknown"):
            assert client.post(f"/api/filings/{filing_id}/prepare").status_code == 403


def test_preparation_access_env_is_validated(monkeypatch):
    monkeypatch.setenv("FILING_PREPARATION_ACCESS", "operator")
    assert Settings.from_env().preparation_access == "operator"
    monkeypatch.setenv("FILING_PREPARATION_ACCESS", "invalid")
    with pytest.raises(ValueError, match="FILING_PREPARATION_ACCESS"):
        Settings.from_env()
