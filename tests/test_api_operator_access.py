import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings


def test_operator_mode_lists_ready_filings_and_refuses_prepare(local_corpus, local_models):
    ready = local_corpus.prepare_selected("NVDA", 2026)
    embedding_calls = local_models[1].call_count
    with TestClient(create_app(store=local_corpus, settings=Settings(preparation_access="operator"))) as client:
        response = client.get("/api/filings")
        assert response.status_code == 200
        assert [(filing["filing_id"], filing["status"]) for filing in response.json()] == [(ready.filing_id, "ready")]
        for filing_id in (ready.filing_id, "0-0000000000-14-000001", "unknown"):
            assert client.post(f"/api/filings/{filing_id}/prepare").status_code == 403
    assert local_models[1].call_count == embedding_calls
    assert {filing.filing_id for filing in local_corpus.prepared()} == {ready.filing_id}


def test_preparation_access_env_is_validated(monkeypatch):
    monkeypatch.setenv("FILING_PREPARATION_ACCESS", "operator")
    assert Settings.from_env().preparation_access == "operator"
    monkeypatch.setenv("FILING_PREPARATION_ACCESS", "invalid")
    with pytest.raises(ValueError, match="FILING_PREPARATION_ACCESS"):
        Settings.from_env()
