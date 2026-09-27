import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
import httpx
import requests

from api.main import create_app
from api.settings import Settings
from tests.test_api_chat import Catalog, prepared_filing


def _response(payload: dict) -> Mock:
    response = Mock(status_code=200)
    response.json.return_value = payload
    return response


def test_chat_rejects_excess_generation_and_recovers_after_release(tmp_path):
    filing = prepared_filing(tmp_path, "NVDA")
    entered = threading.Event()
    release = threading.Event()
    embedding_calls = []

    def ollama_post(*, url, json, timeout):
        if url.endswith("/api/embed"):
            embedding_calls.append(json["input"])
            return _response({"embeddings": [[1.0, 0.0]]})
        if not entered.is_set():
            entered.set()
            assert release.wait(timeout=5)
        return _response({"response": "Answer"})

    request = {"filing_id": filing.filing_id, "question": "What happened?"}
    app = create_app(store=Catalog([filing]), settings=Settings(max_concurrent_generations=1))
    with patch("etl_pipeline.ollama.requests.post", side_effect=ollama_post):
        with TestClient(app) as client, ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(client.post, "/api/chat", json=request)
            try:
                assert entered.wait(timeout=3)
                rejected = client.post("/api/chat", json={
                    "filing_id": filing.filing_id, "question": "Different question?",
                })
                health = client.get("/api/health")
                assert embedding_calls == [["what happened?"]]
            finally:
                release.set()
            completed = first.result(timeout=5)
            later = client.post("/api/chat", json=request)

    assert rejected.status_code == 503
    assert health.status_code == 200
    assert "capacity" in rejected.json()["detail"].lower()
    assert completed.status_code == later.status_code == 200


def test_simultaneous_queries_keep_distinct_filing_evidence(tmp_path):
    first = prepared_filing(tmp_path, "NVDA")
    second = prepared_filing(tmp_path, "AMZN")
    barrier = threading.Barrier(2)

    def ollama_post(*, url, json, timeout):
        if url.endswith("/api/embed"):
            return _response({"embeddings": [[1.0, 0.0]]})
        barrier.wait(timeout=5)
        text = "NVDA" if "NVDA filing evidence" in json["prompt"] else "AMZN"
        return _response({"response": f"{text} answer"})

    app = create_app(store=Catalog([first, second]), settings=Settings(max_concurrent_generations=2))
    with patch("etl_pipeline.ollama.requests.post", side_effect=ollama_post):
        with TestClient(app) as client, ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(client.post, "/api/chat", json={"filing_id": item.filing_id, "question": "Same?"})
                for item in (first, second)
            ]
            results = [future.result(timeout=7) for future in futures]

    assert [result.status_code for result in results] == [200, 200]
    assert [result.json()["answer"] for result in results] == ["NVDA answer", "AMZN answer"]
    assert [result.json()["retrieved_chunks"][0]["text"] for result in results] == [
        "NVDA filing evidence", "AMZN filing evidence",
    ]


def test_generation_timeout_releases_capacity_for_next_question(tmp_path):
    filing = prepared_filing(tmp_path, "NVDA")
    attempts = 0

    def ollama_post(*, url, json, timeout):
        nonlocal attempts
        if url.endswith("/api/embed"):
            return _response({"embeddings": [[1.0, 0.0]]})
        attempts += 1
        if attempts == 1:
            raise requests.Timeout("generation timed out")
        return _response({"response": "Recovered answer"})

    request = {"filing_id": filing.filing_id, "question": "What happened?"}
    with patch("etl_pipeline.ollama.requests.post", side_effect=ollama_post):
        with TestClient(create_app(store=Catalog([filing]))) as client:
            timeout = client.post("/api/chat", json=request)
            recovered = client.post("/api/chat", json=request)

    assert timeout.status_code == 504
    assert recovered.status_code == 200
    assert recovered.json()["answer"] == "Recovered answer"


def test_health_remains_responsive_under_excess_chat_load(tmp_path):
    filing = prepared_filing(tmp_path, "NVDA")
    started = threading.Event()
    release = threading.Event()
    embedded = []

    def ollama_post(*, url, json, timeout):
        if url.endswith("/api/embed"):
            embedded.append(json["input"])
            return _response({"embeddings": [[1.0, 0.0]]})
        started.set()
        assert release.wait(timeout=5)
        return _response({"response": "Answer"})

    async def run():
        app = create_app(store=Catalog([filing]), settings=Settings(max_concurrent_generations=1))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = asyncio.create_task(client.post("/api/chat", json={
                "filing_id": filing.filing_id, "question": "First question?",
            }))
            try:
                assert await asyncio.to_thread(started.wait, 3)
                excess = await asyncio.wait_for(asyncio.gather(*[
                    client.post("/api/chat", json={
                        "filing_id": filing.filing_id, "question": f"Other question {i}?",
                    }) for i in range(50)
                ]), timeout=3)
                health = await asyncio.wait_for(client.get("/api/health"), timeout=1)
                assert [item.status_code for item in excess] == [503] * 50
                assert health.status_code == 200
                assert embedded == [["first question?"]]
            finally:
                release.set()
                assert (await first).status_code == 200

    with patch("etl_pipeline.ollama.requests.post", side_effect=ollama_post):
        asyncio.run(run())
