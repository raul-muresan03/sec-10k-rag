from typing import List, Tuple

from etl_pipeline.ollama import OllamaInvalidResponse, post_json
from etl_pipeline import cloud_http
from etl_pipeline.model_config import ModelConfig
from etl_pipeline.model_errors import ModelInputError, ModelInvalidResponse
from etl_pipeline.vector_store import get_most_similar_chunks

SYSTEM_PROMPT = (
    "You are a Senior Financial Analyst expert in SEC filings (10-K). "
    "Use the provided context to answer the user's question. "
    "\n\n"
    "Rules:\n"
    "1. If you cannot find the exact answer in the context, strictly state: "
    "'Information not available in the provided context'. Do not hallucinate numbers.\n"
    "2. Use a professional, concise tone.\n"
    "\n\n"
)

OLLAMA_METRIC_FIELDS = (
    "total_duration",
    "load_duration",
    "prompt_eval_count",
    "prompt_eval_duration",
    "eval_count",
    "eval_duration",
)


def get_llm_response(
    user_prompt: str,
    chunks: List[Tuple[float, str]],
    ollama_llm_model_name: str,
    *, config: ModelConfig | None = None,
) -> Tuple[str, dict]:
    config = config if config is not None else ModelConfig.from_env(model=ollama_llm_model_name)
    chunks_text: List[str] = []
    for _, text in chunks:
        chunks_text.append(text)

    combined_chunks = "\n".join(chunks_text)

    if config.runtime == "cloud":
        if not user_prompt.strip() or len(user_prompt.encode("utf-8")) > 2000:
            raise ModelInputError("Cloud question must be nonempty and at most 2000 UTF-8 bytes")
        if len(chunks) > 10 or len(combined_chunks.encode("utf-8")) > 16000:
            raise ModelInputError("Cloud context exceeds 10 chunks or 16000 UTF-8 bytes")
        result = cloud_http.post_json(
            "groq", "https://api.groq.com/openai/v1/chat/completions", config.groq_api_key,
            {"model": config.model, "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context: {combined_chunks}\n\nQuestion: {user_prompt}"},
            ], "max_completion_tokens": 512, "include_reasoning": False},
            timeout=config.cloud_timeout_seconds,
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

    data = {
        "model": ollama_llm_model_name,
        "prompt": f"{SYSTEM_PROMPT} Context: {combined_chunks} \n\n Use Question: {user_prompt}",
        "stream": False
    }

    llm_response = post_json("/api/generate", data)
    answer = llm_response.get("response")
    if not isinstance(answer, str) or not answer.strip():
        raise OllamaInvalidResponse("Generation response has no answer")
    metrics = {
        field: llm_response[field]
        for field in OLLAMA_METRIC_FIELDS
        if field in llm_response
    }
    return answer, metrics

if __name__ == "__main__":
    from etl_pipeline.pipeline import ensure_index

    user_prompt = "Who is the CEO of NVIDIA?"
    relevant_chunks = get_most_similar_chunks(user_prompt, 5, ensure_index("NVDA", 2026))
    response, _ = get_llm_response(user_prompt, relevant_chunks, "gemma3:1b")
    print(response)
