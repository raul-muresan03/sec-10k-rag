from unittest.mock import Mock, patch

import pytest
import requests

from etl_pipeline import ollama


def test_post_json_uses_configured_ollama_url_and_timeout(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434/")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "3")
    response = Mock(status_code=200)
    response.json.return_value = {"response": "answer"}

    with patch.object(ollama.requests, "post", return_value=response) as post:
        assert ollama.post_json("/api/generate", {"stream": False}) == {"response": "answer"}

    post.assert_called_once_with(
        url="http://ollama:11434/api/generate", json={"stream": False}, timeout=3.0,
    )


def test_post_json_classifies_timeouts_and_unavailable_service():
    with patch.object(ollama.requests, "post", side_effect=requests.Timeout):
        with pytest.raises(ollama.OllamaTimeout):
            ollama.post_json("/api/generate", {})

    response = Mock(status_code=503)
    with patch.object(ollama.requests, "post", return_value=response):
        with pytest.raises(ollama.OllamaUnavailable, match="503"):
            ollama.post_json("/api/generate", {})


def test_post_json_rejects_malformed_success_payload():
    response = Mock(status_code=200)
    response.json.return_value = []
    with patch.object(ollama.requests, "post", return_value=response):
        with pytest.raises(ollama.OllamaInvalidResponse):
            ollama.post_json("/api/generate", {})
