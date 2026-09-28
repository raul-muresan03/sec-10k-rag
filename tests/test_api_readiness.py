from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from api.main import create_app
from etl_pipeline.ollama import OllamaTimeout


class Catalog:
    def __init__(self, valid=True):
        self.valid = valid

    def catalog(self):
        if not self.valid:
            raise ValueError("Invalid manifest")
        return {"filing": object()}


def test_ready_requires_catalog_and_both_models_not_prepared_indexes():
    models = [{"name": "nomic-embed-text:latest"}, {"name": "gemma3:1b"}]
    with patch("api.main.installed_models", return_value=models):
        with TestClient(create_app(store=Catalog())) as client:
            response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_explains_invalid_manifest_without_affecting_health():
    with TestClient(create_app(store=Catalog(False))) as client:
        ready = client.get("/api/ready")
        health = client.get("/api/health")

    assert ready.status_code == 503
    assert ready.json()["status"] == "not_ready"
    assert health.json() == {"status": "ok"}


def test_ready_reports_unavailable_ollama_or_missing_generation_model():
    with patch("api.main.installed_models", side_effect=OllamaTimeout("Ollama timed out")):
        with TestClient(create_app(store=Catalog())) as client:
            timeout = client.get("/api/ready")
    assert timeout.status_code == 503
    assert "Ollama" in timeout.json()["reason"]

    with patch("api.main.installed_models", return_value=[{"name": "nomic-embed-text:latest"}]):
        with TestClient(create_app(store=Catalog())) as client:
            missing = client.get("/api/ready")
    assert missing.status_code == 503
    assert "gemma3:1b" in missing.json()["reason"]


def test_ready_rejects_malformed_ollama_model_metadata():
    response = Mock(status_code=200)
    response.json.return_value = {"models": [{"name": []}]}
    with patch("etl_pipeline.ollama.requests.get", return_value=response):
        with TestClient(create_app(store=Catalog())) as client:
            ready = client.get("/api/ready")

    assert ready.status_code == 503
    assert ready.json()["status"] == "not_ready"
