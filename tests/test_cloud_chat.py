from dataclasses import replace
import asyncio
import json
from unittest.mock import patch

from fastapi.testclient import TestClient
import httpx

from api.main import create_app
from api.settings import Settings
from etl_pipeline.runtime_snapshot import SnapshotStore
import pytest


def test_cloud_api_reads_export_and_answers_without_raw_or_ollama(
    runtime_export, local_corpus, cloud_config, cloud_http,
):
    for filing in local_corpus.catalog().values():
        filing.path.unlink()
    store = SnapshotStore(runtime_export)
    filing = store.resolve("NVDA", 2026)

    def respond(request):
        if "cloudflare" in str(request.url):
            return httpx.Response(200, json={"success": True, "result": {"data": [[1.0] + [0.0] * 383]}})
        return httpx.Response(200, json={"choices": [
            {"finish_reason": "stop", "message": {"content": "Grounded cloud answer"}},
        ]})

    calls = cloud_http(respond)
    settings = Settings(model=cloud_config.model, preparation_access="operator", models=cloud_config)
    with patch("requests.get", side_effect=AssertionError("Cloud contacted Ollama")):
        with patch("requests.post", side_effect=AssertionError("Cloud contacted Ollama")):
            with TestClient(create_app(store=store, settings=settings)) as client:
                assert client.get("/api/ready").status_code == 200
                assert not calls
                assert len(client.get("/api/filings").json()) == 2
                assert client.post(f"/api/filings/{filing.filing_id}/prepare").status_code == 403
                response = client.post("/api/chat", json={"filing_id": filing.filing_id, "question": "Revenue?"})
    assert response.status_code == 200
    assert response.json()["answer"] == "Grounded cloud answer"
    assert response.json()["retrieved_chunks"][0]["text"] == "NVDA evidence"
    assert [request.url.host for request in calls] == ["api.cloudflare.com", "api.groq.com"]
    assert json.loads(calls[0].content)["text"][0].endswith("Revenue?")


@pytest.mark.parametrize("slow_stage", ["embedding", "generation"])
def test_cloud_api_uses_one_total_budget_and_stops_on_timeout(
    runtime_export, cloud_config, cloud_http, slow_stage,
):
    async def respond(request):
        if request.url.host == "api.cloudflare.com":
            await asyncio.sleep(0.5 if slow_stage == "embedding" else 0.05)
            return httpx.Response(200, json={"success": True, "result": {"data": [[1.0] + [0.0] * 383]}})
        await asyncio.sleep(0.4)
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop", "message": {"content": "Too late"},
        }]})

    calls = cloud_http(respond)
    models = replace(cloud_config, query_timeout_seconds=0.3)
    settings = Settings(model=models.model, models=models, preparation_access="operator")
    store = SnapshotStore(runtime_export)
    with TestClient(create_app(store=store, settings=settings)) as client:
        response = client.post("/api/chat", json={
            "filing_id": store.resolve("NVDA", 2026).filing_id, "question": f"New budget probe {slow_stage}?",
        })
    assert response.status_code == 504
    assert [request.url.host for request in calls] == (
        ["api.cloudflare.com"] if slow_stage == "embedding" else ["api.cloudflare.com", "api.groq.com"]
    )
