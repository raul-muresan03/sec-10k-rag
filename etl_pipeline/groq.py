"""Bounded Groq generation with validated final answers."""

from etl_pipeline import cloud_http
from etl_pipeline.model_config import ModelConfig
from etl_pipeline.model_errors import ModelInputError, ModelInvalidResponse


def generate(question: str, chunks: list[tuple[float, str]], system_prompt: str, config: ModelConfig,
             *, deadline: float | None = None) -> tuple[str, dict]:
    if not question.strip() or len(question.encode("utf-8")) > 2000:
        raise ModelInputError("Cloud question must be nonempty and at most 2000 UTF-8 bytes")
    if len(chunks) > 10:
        raise ModelInputError("Cloud context exceeds 10 chunks")
    context = "\n".join(text for _, text in chunks)
    if len(context.encode("utf-8")) > 16000:
        raise ModelInputError("Cloud context exceeds 16000 UTF-8 bytes")
    result = cloud_http.post_json(
        "groq", "https://api.groq.com/openai/v1/chat/completions", config.groq_api_key,
        {"model": config.model, "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"},
        ], "max_completion_tokens": 512, "include_reasoning": False},
        timeout=config.cloud_timeout_seconds, deadline=deadline,
    )
    try:
        choice = result["choices"][0]
        answer = choice["message"]["content"]
        valid = choice["finish_reason"] == "stop" and isinstance(answer, str) and answer.strip()
    except (KeyError, IndexError, TypeError):
        raise ModelInvalidResponse("groq returned an invalid answer") from None
    if not valid or len(answer) > 8192:
        raise ModelInvalidResponse("groq returned a blank, truncated or oversized answer")
    return answer, {"provider": "groq", "usage": result.get("usage", {})}
