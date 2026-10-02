import json

import httpx
import pytest

from etl_pipeline.chunker import paragraphs_to_embeddings, text_to_embedding
from etl_pipeline.model_errors import ModelInputError, ModelInvalidResponse, ModelRateLimited, ModelTimeout


def test_cloud_embeddings_use_cloudflare_without_ollama(cloud_config, cloud_http):
    vectors = [[1.0] + [0.0] * 383, [0.0, 1.0] + [0.0] * 382]
    calls = cloud_http(lambda request: httpx.Response(200, json={
        "success": True, "result": {"shape": [2, 384], "data": vectors, "pooling": "mean"},
    }))
    assert paragraphs_to_embeddings(["first", "second"], config=cloud_config) == vectors
    assert len(calls) == 1
    assert str(calls[0].url) == (
        "https://api.cloudflare.com/client/v4/accounts/" + "a" * 32
        + "/ai/run/@cf/baai/bge-small-en-v1.5"
    )
    assert calls[0].headers["Authorization"] == "Bearer test-cloudflare-secret"
    assert json.loads(calls[0].content) == {"text": ["first", "second"], "pooling": "mean"}


@pytest.mark.parametrize("vector", [
    [], [1.0] * 768, [0.0] * 384, [True] + [1.0] * 383,
    [float("nan")] + [1.0] * 383, [float("inf")] + [1.0] * 383,
    ["bad"] + [1.0] * 383, [1e308] * 384,
])
def test_cloud_embeddings_reject_invalid_dimensions_values_and_norms(cloud_config, cloud_http, vector):
    cloud_http(lambda request: httpx.Response(200, content=json.dumps({
        "success": True, "result": {"data": [vector]},
    })))
    with pytest.raises(ModelInvalidResponse):
        paragraphs_to_embeddings(["first"], config=cloud_config)


@pytest.mark.parametrize("payload", [
    {}, {"success": False, "errors": [{"message": "test-cloudflare-secret"}]},
    {"success": True, "result": None}, {"success": True, "result": {"data": None}},
    {"success": True, "result": {"data": []}},
    {"success": True, "result": {"data": [[1.0] * 384], "shape": [1, 768]}},
    {"success": True, "result": {"data": [[1.0] * 384], "pooling": "cls"}},
])
def test_cloud_embeddings_validate_envelope_count_shape_and_pooling(cloud_config, cloud_http, payload):
    cloud_http(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(ModelInvalidResponse) as failure:
        paragraphs_to_embeddings(["first"], config=cloud_config)
    assert "secret" not in str(failure.value)


@pytest.mark.parametrize("texts", [[], [""], ["first"] * 101, ["a" * 481], ["🙂" * 121]],
                         ids=["empty-batch", "blank", "batch-size", "input-size", "unicode"])
def test_cloud_embeddings_reject_unbounded_batches_before_http(cloud_config, cloud_http, texts):
    calls = cloud_http(lambda request: pytest.fail("Invalid batch reached the cloud"))
    with pytest.raises(ModelInputError):
        paragraphs_to_embeddings(texts, config=cloud_config)
    assert not calls


def test_question_embedding_uses_the_same_cloud_configuration(cloud_config, cloud_http):
    vector = [1.0] * 384
    calls = cloud_http(lambda request: httpx.Response(200, json={
        "success": True, "result": {"data": [vector]},
    }))
    assert text_to_embedding("Revenue?", config=cloud_config) == vector
    assert json.loads(calls[0].content) == {"text": ["Revenue?"], "pooling": "mean"}


@pytest.mark.parametrize("quota", [True, False])
def test_cloud_embeddings_preserve_timeout_and_quota_failures(cloud_config, cloud_http, quota):
    def send(request):
        if not quota:
            raise httpx.ReadTimeout("test-cloudflare-secret")
        return httpx.Response(429, headers={"Retry-After": "5"})

    calls = cloud_http(send)
    with pytest.raises(ModelRateLimited if quota else ModelTimeout) as failure:
        paragraphs_to_embeddings(["first"], config=cloud_config)
    assert "secret" not in str(failure.value)
    assert len(calls) == 1
