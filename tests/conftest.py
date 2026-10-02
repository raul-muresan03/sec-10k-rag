from pathlib import Path
import inspect
import json
from unittest.mock import Mock

import httpx
import pytest
import requests

import etl_pipeline
from etl_pipeline.model_config import CLOUD_GENERATION_MODEL, ModelConfig
from tests.filing_helpers import filing_corpus


@pytest.fixture
def data_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    monkeypatch.setattr(etl_pipeline, "DATA_DIR", data_directory)
    return data_directory


@pytest.fixture
def cloud_config():
    return ModelConfig(runtime="cloud", model=CLOUD_GENERATION_MODEL, groq_api_key="test-groq-secret",
                       cloudflare_api_token="test-cloudflare-secret", cloudflare_account_id="a" * 32)


@pytest.fixture
def cloud_http(monkeypatch):
    def install(handler):
        calls = []

        async def send(self, request):
            await request.aread()
            calls.append(request)
            reply = handler(request)
            return await reply if inspect.isawaitable(reply) else reply

        monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", send)
        return calls

    return install


@pytest.fixture
def local_corpus(tmp_path):
    return filing_corpus(tmp_path)


@pytest.fixture
def local_models(monkeypatch):
    def reply(payload):
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(payload).encode()
        return response

    def send(*, url, json, timeout):
        return reply({"embeddings": [[1.0, 0.0] for _ in json["input"]]} if url.endswith("/api/embed")
                     else {"response": "Grounded answer"})

    get = Mock(return_value=reply({"models": [{"name": "nomic-embed-text", "digest": "a" * 64}]}))
    post = Mock(side_effect=send)
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(requests, "post", post)
    return get, post
