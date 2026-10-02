"""Cloudflare embedding adapter; full token-aware indexing is delivered separately."""

from etl_pipeline.cloud_http import post_json
from math import hypot, isfinite

from etl_pipeline.model_config import CLOUD_EMBEDDING_DIMENSION, ModelConfig
from etl_pipeline.model_errors import ModelInputError, ModelInvalidResponse


def embed(texts: list[str], config: ModelConfig, *, deadline: float | None = None) -> list[list[float]]:
    if not 1 <= len(texts) <= 100:
        raise ModelInputError("Cloud embedding batch must contain 1 to 100 texts")
    if any(not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 480 for text in texts):
        raise ModelInputError(
            "Cloud embedding input must be nonempty and at most 480 UTF-8 bytes pending token validation"
        )
    endpoint = f"https://api.cloudflare.com/client/v4/accounts/{config.cloudflare_account_id}/ai/run/"
    result = post_json(
        "cloudflare", endpoint + config.embedding_model,
        config.cloudflare_api_token, {"text": texts, "pooling": "mean"}, timeout=config.cloud_timeout_seconds,
        deadline=deadline,
    )
    output = result.get("result")
    if result.get("success") is not True or not isinstance(output, dict):
        raise ModelInvalidResponse("cloudflare returned an invalid embedding payload")
    vectors = output.get("data")
    if not isinstance(vectors, list) or len(vectors) != len(texts):
        raise ModelInvalidResponse("cloudflare embedding count does not match batch size")
    if output.get("shape", [len(texts), CLOUD_EMBEDDING_DIMENSION]) != [len(texts), CLOUD_EMBEDDING_DIMENSION]:
        raise ModelInvalidResponse("cloudflare returned an incompatible embedding shape")
    if output.get("pooling", "mean") != "mean":
        raise ModelInvalidResponse("cloudflare returned incompatible embedding pooling")
    for vector in vectors:
        if (not isinstance(vector, list) or len(vector) != CLOUD_EMBEDDING_DIMENSION
                or any(type(value) not in (int, float) or not isfinite(value) for value in vector)
                or not 0 < hypot(*vector) < float("inf")):
            raise ModelInvalidResponse("cloudflare returned an invalid embedding vector")
    return vectors
