from typing import List, Tuple
from pathlib import Path
from math import isfinite
from etl_pipeline.chunker import EMBEDDING_MODEL, text_to_embedding, get_similarity_score
import json

prompt_cache = {}


def load_index(index_path: Path) -> tuple[list[str], list[list[float]]]:
    with index_path.open(encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid index: {index_path}")
    chunks, embeddings = data.get("chunks"), data.get("embeddings")
    if not isinstance(chunks, list) or not chunks or not isinstance(embeddings, list):
        raise ValueError(f"Invalid index chunks/embeddings: {index_path}")
    if len(chunks) != len(embeddings) or any(not isinstance(chunk, str) or not chunk for chunk in chunks):
        raise ValueError(f"Invalid index chunk count or text: {index_path}")
    dimension = len(embeddings[0]) if isinstance(embeddings[0], list) else 0
    if not dimension or any(
        not isinstance(vector, list) or len(vector) != dimension
        or any(type(value) not in (int, float) or not isfinite(value) for value in vector)
        for vector in embeddings
    ):
        raise ValueError(f"Invalid embedding dimensions/values: {index_path}")
    return chunks, embeddings


def get_most_similar_chunks(
    prompt: str, top_n: int, index_path: Path,
) -> List[Tuple[float, str]]:
    if top_n < 1:
        raise ValueError("top_n must be positive")
    chunks, embeddings = load_index(index_path)
    cleaned_prompt= prompt.strip().lower()
    cache_key = (EMBEDDING_MODEL, str(index_path.resolve()), cleaned_prompt)

    if cache_key in prompt_cache:
        prompt_embedding = prompt_cache[cache_key]
    else:
        prompt_embedding = text_to_embedding(cleaned_prompt)
    if (
        not isinstance(prompt_embedding, list)
        or len(prompt_embedding) != len(embeddings[0])
        or any(type(value) not in (int, float) or not isfinite(value) for value in prompt_embedding)
    ):
        raise ValueError(f"Invalid question embedding for index: {index_path}")
    prompt_cache[cache_key] = prompt_embedding

    scores = []
    for i in range(len(chunks)):
        score = get_similarity_score(embeddings[i], prompt_embedding)
        scores.append([score, chunks[i]])

    scores.sort(reverse=True)
    return scores[:top_n]


if __name__ == "__main__":
    from etl_pipeline.pipeline import ensure_index

    result = get_most_similar_chunks("Who is the CEO in Nvidia?", 5, ensure_index("NVDA", 2026))
    for score, chunk in result:
        print("Score:", score)
        print(chunk)
        print("-----------------------------")
