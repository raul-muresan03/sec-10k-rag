import json
import asyncio
from dataclasses import replace
import time

import httpx
import pytest

from etl_pipeline.model_errors import (
    ModelInputError, ModelInvalidResponse, ModelRateLimited, ModelTimeout, ModelUnavailable,
)
from etl_pipeline.rag_engine import get_llm_response
from etl_pipeline.chunker import text_to_embedding


def response(payload, status=200, headers=None):
    return httpx.Response(status, json=payload, headers=headers)


def test_cloud_generation_uses_groq_with_bounded_output(cloud_config, cloud_http):
    reply = response({
        "model": "openai/gpt-oss-20b",
        "choices": [{"message": {"content": "Grounded answer"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 40, "completion_tokens": 20, "total_tokens": 60},
    })
    calls = cloud_http(lambda request: reply)
    answer, metrics = get_llm_response("Revenue?", [(0.9, "Revenue evidence")], cloud_config.model,
                                       config=cloud_config)
    assert answer == "Grounded answer"
    assert metrics["provider"] == "groq"
    assert metrics["usage"]["total_tokens"] == 60
    assert len(calls) == 1
    request = calls[0]
    payload = json.loads(request.content)
    assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-groq-secret"
    assert payload["model"] == "openai/gpt-oss-20b"
    assert payload["max_completion_tokens"] == 512
    assert payload["include_reasoning"] is False
    assert "Revenue evidence" in str(payload["messages"])
    assert "Revenue?" in str(payload["messages"])


@pytest.mark.parametrize("upstream, expected", [
    (httpx.ReadTimeout("test-groq-secret"), ModelTimeout),
    (httpx.ConnectError("test-groq-secret"), ModelUnavailable),
    (response({"error": "test-groq-secret"}, 503), ModelUnavailable),
    (response({}, 302, {"Location": "https://untrusted.invalid"}), ModelUnavailable),
])
def test_groq_transport_errors_do_not_leak_upstream_data_or_follow_redirects(
    cloud_config, cloud_http, upstream, expected,
):
    def send(request):
        if isinstance(upstream, Exception):
            raise upstream
        return upstream

    calls = cloud_http(send)
    with pytest.raises(expected) as failure:
        get_llm_response("Revenue?", [], cloud_config.model, config=cloud_config)
    assert "secret" not in str(failure.value)
    assert len(calls) == 1


@pytest.mark.parametrize("retry_header, expected", [("12", 12), ("99999", 300), ("garbage", 60), ("0", 1)])
def test_groq_quota_is_not_retried_and_has_safe_bounded_retry(cloud_config, cloud_http, retry_header, expected):
    calls = cloud_http(lambda request: response({"error": "test-groq-secret"}, 429, {"Retry-After": retry_header}))
    with pytest.raises(ModelRateLimited) as failure:
        get_llm_response("Revenue?", [], cloud_config.model, config=cloud_config)
    assert failure.value.retry_after == expected
    assert "secret" not in str(failure.value)
    assert len(calls) == 1


@pytest.mark.parametrize("reply", [
    httpx.Response(200, content=b"not json test-groq-secret"),
    httpx.Response(200, content=b'{"nested":' + b"[" * 10_000 + b"0" + b"]" * 10_000 + b"}"),
    response([]), response({}), response({"choices": [None]}),
    response({"choices": [{"message": {"content": " "}, "finish_reason": "stop"}]}),
    response({"choices": [{"message": {"content": "Incomplete"}, "finish_reason": "length"}]}),
    response({"choices": [{"message": {"content": "a" * 8193}, "finish_reason": "stop"}]}),
])
def test_groq_rejects_invalid_blank_truncated_or_unbounded_answers(cloud_config, cloud_http, reply):
    cloud_http(lambda request: reply)
    with pytest.raises(ModelInvalidResponse):
        get_llm_response("Revenue?", [], cloud_config.model, config=cloud_config)


@pytest.mark.parametrize("question, chunks", [
    (" ", []), ("q" * 2001, []), ("🙂" * 501, []),
    ("Revenue?", [(1, "c" * 16001)]), ("Revenue?", [(1, "evidence")] * 11),
], ids=["blank", "long", "unicode", "context", "chunk-count"])
def test_cloud_generation_rejects_unbounded_input_before_http(cloud_config, cloud_http, question, chunks):
    calls = cloud_http(lambda request: pytest.fail("Invalid input reached the cloud"))
    with pytest.raises(ModelInputError):
        get_llm_response(question, chunks, cloud_config.model, config=cloud_config)
    assert not calls


def test_cloud_generation_cancels_the_request_at_its_total_deadline(cloud_config, cloud_http):
    cancelled = []

    async def slow_reply(request):
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.append(True)

    cloud_http(slow_reply)
    started = time.monotonic()
    with pytest.raises(ModelTimeout):
        get_llm_response("Revenue?", [], cloud_config.model,
                         config=replace(cloud_config, cloud_timeout_seconds=0.05))
    assert time.monotonic() - started < 1
    assert cancelled == [True]


def test_cloud_response_body_is_bounded_and_closed(cloud_config, cloud_http):
    closed = []

    class HugeBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(4):
                yield b"x" * 1_048_576

        async def aclose(self):
            closed.append(True)

    cloud_http(lambda request: httpx.Response(200, stream=HugeBody()))
    with pytest.raises(ModelInvalidResponse, match="size"):
        get_llm_response("Revenue?", [], cloud_config.model, config=cloud_config)
    assert closed == [True]


def test_cloud_embedding_and_generation_share_one_deadline(cloud_config, cloud_http):
    async def send(request):
        if request.url.host == "api.cloudflare.com":
            await asyncio.sleep(0.02)
            return httpx.Response(200, json={"success": True, "result": {"data": [[1.0] * 384]}})
        await asyncio.sleep(10)

    calls = cloud_http(send)
    started = time.monotonic()
    deadline = started + 0.3
    text_to_embedding("Revenue?", config=cloud_config, deadline=deadline)
    with pytest.raises(ModelTimeout):
        get_llm_response("Revenue?", [], cloud_config.model, config=cloud_config, deadline=deadline)
    assert time.monotonic() - started < 1
    assert len(calls) == 2


def test_expired_cloud_deadline_does_not_start_a_request(cloud_config, cloud_http):
    calls = cloud_http(lambda request: pytest.fail("Expired request reached the cloud"))
    with pytest.raises(ModelTimeout):
        get_llm_response("Revenue?", [], cloud_config.model, config=cloud_config, deadline=time.monotonic() - 1)
    assert not calls


def test_environment_selected_cloud_embedding_preserves_deadline(cloud_config, cloud_http, monkeypatch):
    for name, value in {
        "RAG_RUNTIME": "cloud", "RAG_MODEL": cloud_config.model,
        "GROQ_API_KEY": cloud_config.groq_api_key,
        "CLOUDFLARE_API_TOKEN": cloud_config.cloudflare_api_token,
        "CLOUDFLARE_ACCOUNT_ID": cloud_config.cloudflare_account_id,
    }.items():
        monkeypatch.setenv(name, value)
    calls = cloud_http(lambda request: pytest.fail("Expired environment-selected request reached the cloud"))
    with pytest.raises(ModelTimeout):
        text_to_embedding("Revenue?", deadline=time.monotonic() - 1)
    assert not calls
