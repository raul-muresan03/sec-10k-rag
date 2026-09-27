from unittest.mock import Mock, patch

import pytest

from etl_pipeline.embedding_model import embedding_model_digest


def test_embedding_model_digest_resolves_latest_tag():
    digest = "a" * 64
    response = Mock()
    response.json.return_value = {"models": [{"name": "nomic-embed-text:latest", "digest": digest}]}
    with patch("etl_pipeline.embedding_model.requests.get", return_value=response) as get:
        assert embedding_model_digest("nomic-embed-text") == digest
    get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)


def test_embedding_model_digest_rejects_unknown_or_invalid_model():
    response = Mock()
    response.json.return_value = {"models": [{"name": "other-model", "digest": "a" * 64}]}
    with patch("etl_pipeline.embedding_model.requests.get", return_value=response):
        with pytest.raises(RuntimeError, match="not installed"):
            embedding_model_digest("nomic-embed-text")

    response.json.return_value = {"models": [{"name": "nomic-embed-text:latest", "digest": "invalid"}]}
    with patch("etl_pipeline.embedding_model.requests.get", return_value=response):
        with pytest.raises(RuntimeError, match="Invalid Ollama digest"):
            embedding_model_digest("nomic-embed-text")
