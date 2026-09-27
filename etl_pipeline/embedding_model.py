"""Resolve the immutable Ollama identity of the embedding model."""

import re

import requests


def embedding_model_digest(model_tag: str) -> str:
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json()["models"]
    except (requests.RequestException, ValueError, KeyError, TypeError) as error:
        raise RuntimeError(f"Could not inspect Ollama embedding model {model_tag}") from error

    if not isinstance(models, list):
        raise RuntimeError("Invalid Ollama model list")
    names = {model_tag, f"{model_tag}:latest"}
    for model in models:
        if not isinstance(model, dict) or model.get("name") not in names:
            continue
        digest = model.get("digest")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RuntimeError(f"Invalid Ollama digest for {model_tag}")
        return digest
    raise RuntimeError(f"Ollama embedding model not installed: {model_tag}")
