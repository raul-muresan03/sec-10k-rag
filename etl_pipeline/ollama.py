"""Synchronous Ollama HTTP boundary shared by indexing and generation."""

from math import isfinite
import os
from urllib.parse import urlsplit

import requests


class OllamaUnavailable(RuntimeError):
    pass


class OllamaTimeout(RuntimeError):
    pass


class OllamaInvalidResponse(RuntimeError):
    pass


def base_url() -> str:
    url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.path:
        raise ValueError("OLLAMA_BASE_URL must be an HTTP(S) origin")
    return url


def timeout_seconds() -> float:
    value = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    if not isfinite(value) or value <= 0:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS must be positive")
    return value


def _json_response(response: requests.Response, endpoint: str) -> dict:
    if response.status_code != 200:
        raise OllamaUnavailable(f"Ollama {endpoint} returned HTTP {response.status_code}")
    try:
        payload = response.json()
    except ValueError as error:
        raise OllamaInvalidResponse(f"Ollama {endpoint} returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise OllamaInvalidResponse(f"Ollama {endpoint} returned an invalid payload")
    return payload


def post_json(endpoint: str, payload: dict, *, timeout: float | None = None) -> dict:
    try:
        response = requests.post(
            url=base_url() + endpoint, json=payload,
            timeout=timeout if timeout is not None else timeout_seconds(),
        )
    except requests.Timeout as error:
        raise OllamaTimeout(f"Ollama {endpoint} timed out") from error
    except requests.RequestException as error:
        raise OllamaUnavailable(f"Ollama {endpoint} is unavailable") from error
    return _json_response(response, endpoint)


def get_json(endpoint: str, *, timeout: float = 5.0) -> dict:
    try:
        response = requests.get(url=base_url() + endpoint, timeout=timeout)
    except requests.Timeout as error:
        raise OllamaTimeout(f"Ollama {endpoint} timed out") from error
    except requests.RequestException as error:
        raise OllamaUnavailable(f"Ollama {endpoint} is unavailable") from error
    return _json_response(response, endpoint)
