from etl_pipeline.vector_store import get_most_similar_chunks
from typing import List, Tuple
import requests

SYSTEM_PROMPT = (
    "You are a Senior Financial Analyst expert in SEC filings (10-K). "
    "Use the provided context to answer the user's question. "
    "\n\n"
    "Rules:\n"
    "1. If you cannot find the exact answer in the context, strictly state: 'Information not available in the provided context'. Do not hallucinate numbers.\n"
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
) -> Tuple[str, dict]:
    chunks_text: List[str] = []
    for _, text in chunks:
        chunks_text.append(text)

    combined_chunks = "\n".join(chunks_text)

    url = "http://localhost:11434/api/generate"
    data = {
        "model": ollama_llm_model_name,
        "prompt": f"{SYSTEM_PROMPT} Context: {combined_chunks} \n\n Use Question: {user_prompt}",
        "stream": False
    }

    response = requests.post(url=url, json=data)
    if response.status_code == 200:
        llm_response = response.json()
        metrics = {
            field: llm_response[field]
            for field in OLLAMA_METRIC_FIELDS
            if field in llm_response
        }
        return llm_response.get("response", ""), metrics
    else:
        print(f"Error: {response.status_code}")
        return "Error", {}

if __name__ == "__main__":
    user_prompt = "Who is the CEO of NVIDIA?"
    relevant_chunks = get_most_similar_chunks(user_prompt, 5)
    response, _ = get_llm_response(user_prompt, relevant_chunks, "gemma3:1b")
    print(response)
