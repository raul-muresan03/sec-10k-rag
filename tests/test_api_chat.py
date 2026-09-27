import json
from unittest.mock import Mock, patch
from uuid import UUID

from fastapi.testclient import TestClient
import pytest

from api.main import create_app
from etl_pipeline.filing_store import PreparedFiling


def prepared_filing(tmp_path, ticker: str) -> PreparedFiling:
    index_path = tmp_path / ticker / "all_chunks_embeddings.json"
    index_path.parent.mkdir()
    index_path.write_text(json.dumps({
        "chunks": [f"{ticker} filing evidence"], "embeddings": [[1.0, 0.0]],
    }))
    return PreparedFiling(
        filing_id=f"{ticker}-accession", ticker=ticker, year=2026,
        accession="accession", sec_url=f"https://www.sec.gov/Archives/{ticker}",
        index_version="a" * 64, index_path=index_path, index_sha256="b" * 64,
        chunk_count=1,
    )


class Catalog:
    def __init__(self, filings):
        self.filings = {filing.filing_id: filing for filing in filings}

    def resolve_id(self, filing_id):
        return self.filings[filing_id]


def test_chat_returns_a_live_answer_and_ranked_evidence_for_selected_filing(tmp_path):
    filing = prepared_filing(tmp_path, "NVDA")
    calls = []

    def ollama_post(*, url, json, timeout):
        calls.append((url, json))
        response = Mock(status_code=200)
        response.json.return_value = (
            {"embeddings": [[1.0, 0.0]]} if url.endswith("/api/embed")
            else {"response": "Grounded NVIDIA answer", "eval_count": 12}
        )
        return response

    with patch("etl_pipeline.ollama.requests.post", side_effect=ollama_post):
        with TestClient(create_app(store=Catalog([filing]))) as client:
            response = client.post("/api/chat", json={
                "filing_id": filing.filing_id, "question": "What happened?",
            })

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Grounded NVIDIA answer"
    assert body["filing_id"] == filing.filing_id
    assert body["model"] == "gemma3:1b"
    assert body["sec_url"] == filing.sec_url
    assert body["retrieved_chunks"] == [{"rank": 1, "score": 1.0, "text": "NVDA filing evidence"}]
    assert UUID(body["request_id"])
    assert body["stage_times_seconds"]["retrieval"] >= 0
    assert body["stage_times_seconds"]["generation"] >= 0
    assert body["stage_times_seconds"]["total"] >= body["stage_times_seconds"]["retrieval"]
    assert [url.rsplit("/", 1)[-1] for url, _ in calls] == ["embed", "generate"]
    assert "NVDA filing evidence" in calls[1][1]["prompt"]


def test_chat_rejects_blank_or_long_questions_and_unknown_filing(tmp_path):
    filing = prepared_filing(tmp_path, "NVDA")
    with TestClient(create_app(store=Catalog([filing]))) as client:
        blank = client.post("/api/chat", json={"filing_id": filing.filing_id, "question": "  "})
        long = client.post("/api/chat", json={"filing_id": filing.filing_id, "question": "q" * 2001})
        unknown = client.post("/api/chat", json={"filing_id": "unknown", "question": "What happened?"})

    assert blank.status_code == 422
    assert long.status_code == 422
    assert unknown.status_code == 404


def test_chat_model_and_retrieval_count_are_server_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_MODEL", "gemma3:4b")
    monkeypatch.setenv("RAG_TOP_N", "1")
    filing = prepared_filing(tmp_path, "NVDA")
    filing.index_path.write_text(json.dumps({
        "chunks": ["closest evidence", "unrelated evidence"],
        "embeddings": [[1.0, 0.0], [0.0, 1.0]],
    }))
    sent_models = []

    def ollama_post(*, url, json, timeout):
        response = Mock(status_code=200)
        if url.endswith("/api/embed"):
            response.json.return_value = {"embeddings": [[1.0, 0.0]]}
        else:
            sent_models.append(json["model"])
            response.json.return_value = {"response": "Grounded answer"}
        return response

    with patch("etl_pipeline.ollama.requests.post", side_effect=ollama_post):
        with TestClient(create_app(store=Catalog([filing]))) as client:
            response = client.post("/api/chat", json={"filing_id": filing.filing_id, "question": "Revenue?"})
            override = client.post("/api/chat", json={
                "filing_id": filing.filing_id, "question": "Revenue?", "model": "untrusted",
            })

    assert response.status_code == 200
    assert response.json()["model"] == "gemma3:4b"
    assert [chunk["text"] for chunk in response.json()["retrieved_chunks"]] == ["closest evidence"]
    assert sent_models == ["gemma3:4b"]
    assert override.status_code == 422


def test_invalid_server_capacity_is_rejected_at_startup(monkeypatch):
    monkeypatch.setenv("RAG_MAX_CONCURRENT_GENERATIONS", "0")
    with pytest.raises(ValueError, match="capacity"):
        create_app()
