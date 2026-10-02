"""Cloudflare embeddings with pinned token limits and explicit mean pooling."""

from etl_pipeline.cloud_http import post_json
from math import hypot, isfinite

from etl_pipeline.model_config import CLOUD_EMBEDDING_DIMENSION, ModelConfig
from etl_pipeline.model_errors import ModelInputError, ModelInvalidResponse
from etl_pipeline.cloud_tokens import BATCH_TEXTS, BATCH_TOKENS, token_count, validated_input


def embed(texts: list[str], config: ModelConfig, *, deadline: float | None = None,
          query: bool = False) -> list[list[float]]:
    if config.runtime != "cloud":
        raise ValueError("Cloud embeddings require the cloud profile")
    if not 1 <= len(texts) <= BATCH_TEXTS:
        raise ModelInputError("Cloud embedding batch must contain 1 to 100 texts")
    texts = [validated_input(text, query=query) for text in texts]
    if sum(token_count(text) for text in texts) > BATCH_TOKENS:
        raise ModelInputError("Cloud embedding batch exceeds 8192 tokens")
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
        try:
            valid = (
                isinstance(vector, list) and len(vector) == CLOUD_EMBEDDING_DIMENSION
                and all(type(value) in (int, float) and isfinite(value) for value in vector)
                and 0 < hypot(*vector) < float("inf")
            )
        except OverflowError:
            valid = False
        if not valid:
            raise ModelInvalidResponse("cloudflare returned an invalid embedding vector")
    return vectors
