from pathlib import Path
import inspect

import httpx
import pytest

import etl_pipeline
from etl_pipeline.model_config import CLOUD_GENERATION_MODEL, ModelConfig


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
