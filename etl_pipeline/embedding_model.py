"""Resolve the immutable Ollama identity of the embedding model."""

import re

from etl_pipeline.ollama import OllamaInvalidResponse, get_json


def installed_models() -> list[dict]:
    models = get_json("/api/tags", timeout=5.0).get("models")
    if not isinstance(models, list) or any(not isinstance(model, dict) for model in models):
        raise OllamaInvalidResponse("Invalid Ollama model list")
    return models


def embedding_model_digest(model_tag: str) -> str:
    names = {model_tag, f"{model_tag}:latest"}
    for model in installed_models():
        if model.get("name") not in names:
            continue
        digest = model.get("digest")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RuntimeError(f"Invalid Ollama digest for {model_tag}")
        return digest
    raise RuntimeError(f"Ollama embedding model not installed: {model_tag}")
