"""Cloud HTTP requests with a wall-clock deadline, without SDK dependencies."""

import asyncio
import json

import httpx

from etl_pipeline.model_errors import (
    ModelInvalidResponse, ModelRateLimited, ModelTimeout, ModelUnavailable, retry_after_seconds,
)

MAX_RESPONSE_BYTES = 2 * 1024 * 1024

async def _post_json(provider: str, url: str, key: str, payload: dict, timeout: float) -> dict:
    async with asyncio.timeout(timeout):
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            async with client.stream("POST", url, headers={"Authorization": f"Bearer {key}"}, json=payload) as reply:
                if reply.status_code == 429:
                    raise ModelRateLimited(provider, retry_after_seconds(reply.headers.get("Retry-After", "")))
                if reply.status_code != 200:
                    raise ModelUnavailable(f"{provider} returned HTTP {reply.status_code}")
                body = bytearray()
                async for chunk in reply.aiter_bytes():
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise ModelInvalidResponse(f"{provider} response exceeds the size limit")
                    body.extend(chunk)
                try:
                    result = json.loads(body)
                except (ValueError, UnicodeError):
                    raise ModelInvalidResponse(f"{provider} returned invalid JSON") from None
                if not isinstance(result, dict):
                    raise ModelInvalidResponse(f"{provider} returned an invalid payload")
                return result


def post_json(provider: str, url: str, key: str, payload: dict, *, timeout: float = 30.0) -> dict:
    try:
        return asyncio.run(_post_json(provider, url, key, payload, timeout))
    except (TimeoutError, httpx.TimeoutException):
        raise ModelTimeout(f"{provider} timed out") from None
    except httpx.HTTPError:
        raise ModelUnavailable(f"{provider} unavailable") from None
