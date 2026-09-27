from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
import pytest
import requests

from api.main import create_app
from tests.test_api_chat import Catalog, prepared_filing


def test_chat_distinguishes_timeout_unavailable_and_malformed_ollama(tmp_path):
    filing = prepared_filing(tmp_path, "NVDA")
    request = {"filing_id": filing.filing_id, "question": "What happened?"}
    with TestClient(create_app(store=Catalog([filing]))) as client:
        with patch("etl_pipeline.ollama.requests.post", side_effect=requests.Timeout):
            timeout = client.post("/api/chat", json=request)
        with patch("etl_pipeline.ollama.requests.post", side_effect=requests.ConnectionError):
            unavailable = client.post("/api/chat", json=request)
        response = Mock(status_code=200)
        response.json.return_value = {"embeddings": "invalid"}
        with patch("etl_pipeline.ollama.requests.post", return_value=response):
            malformed = client.post("/api/chat", json=request)

    assert timeout.status_code == 504
    assert unavailable.status_code == 503
    assert malformed.status_code == 502
    for failure in (timeout, unavailable, malformed):
        assert "answer" not in failure.json()


def test_chat_and_filings_report_missing_indexes_as_unavailable():
    class MissingCatalog:
        def resolve_id(self, filing_id):
            raise RuntimeError("Index not prepared at /private/data/indexes")

        def prepared(self):
            raise RuntimeError("Index corrupted at /private/data/indexes")

    with TestClient(create_app(store=MissingCatalog())) as client:
        chat = client.post("/api/chat", json={"filing_id": "known", "question": "Question?"})
        filings = client.get("/api/filings")

    assert chat.status_code == filings.status_code == 503
    assert "/private/" not in str(chat.json()) + str(filings.json())


@pytest.mark.parametrize("embedding", [None, ["bad", 0.0], [1.0], [float("nan"), 0.0], []])
def test_chat_classifies_invalid_ollama_embedding_as_bad_gateway(tmp_path, embedding):
    filing = prepared_filing(tmp_path, "NVDA")
    response = Mock(status_code=200)
    response.json.return_value = {"embeddings": [embedding]}

    with patch("etl_pipeline.ollama.requests.post", return_value=response):
        with TestClient(create_app(store=Catalog([filing]))) as client:
            result = client.post("/api/chat", json={"filing_id": filing.filing_id, "question": "What happened?"})

    assert result.status_code == 502
    assert result.json()["detail"] == "Ollama returned an invalid response"
