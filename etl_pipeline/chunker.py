from typing import List
import os
from math import isfinite, sqrt
import json
from pathlib import Path

import etl_pipeline
from etl_pipeline.ollama import OllamaInvalidResponse, post_json
from etl_pipeline.model_config import ModelConfig
from etl_pipeline.cloud_embeddings import embed

EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "512"))
EMBEDDING_MODEL = "nomic-embed-text"
MAX_CHUNK_LENGTH = 10000
CHUNK_SEPARATOR = " "
MERGE_SIMILARITY_THRESHOLD = 0.6

def get_similarity_score(first: List[float], second: List[float]) -> float:
    if first is None or second is None:
        return -2

    dot_product = 0
    magnitude_first = 0
    magnitude_second = 0

    for i in range(len(first)):
        dot_product += first[i] * second[i]
        magnitude_first += first[i] * first[i]
        magnitude_second += second[i] * second[i]

    if magnitude_first == 0 or magnitude_second == 0:
        return -2

    magnitude_first = sqrt(magnitude_first)
    magnitude_second = sqrt(magnitude_second)

    cosine_similarity = dot_product / (magnitude_first * magnitude_second)
    return cosine_similarity

def paragraphs_to_embeddings(paragraphs: List[str], *, config: ModelConfig | None = None) -> List[List[float]]:
    config = config if config is not None else ModelConfig.from_env()
    if config.runtime == "cloud":
        return embed(paragraphs, config)
    data = {
        "model": EMBEDDING_MODEL,
        "input": paragraphs,
    }

    embeddings = post_json("/api/embed", data).get("embeddings")
    if not isinstance(embeddings, list):
        raise OllamaInvalidResponse("Embedding response has no embeddings array")
    if len(embeddings) != len(paragraphs):
        raise OllamaInvalidResponse("Embedding count does not match batch size")
    dimension = len(embeddings[0]) if embeddings and isinstance(embeddings[0], list) else 0
    if not dimension or any(
        not isinstance(vector, list) or len(vector) != dimension
        or any(type(value) not in (int, float) or not isfinite(value) for value in vector)
        for vector in embeddings
    ):
        raise OllamaInvalidResponse("Invalid Ollama embedding vector")

    return embeddings


def text_to_embedding(paragraph: str, *, config: ModelConfig | None = None) -> List[float]:
    if config is None:
        return paragraphs_to_embeddings([paragraph])[0]
    return paragraphs_to_embeddings([paragraph], config=config)[0]

def _get_all_paragraphs(document: str) -> List[str]:
    paragraphs = []
    for s in document.split("\n\n"):
        if s.strip():
            paragraphs.append(s)

    return paragraphs

def _get_all_vector_embeddings(paragraphs: List[str]) -> List[List[float]]:
    all_embeddings = []
    batch: List[str] = []
    for start in range(0, len(paragraphs), EMBEDDING_BATCH_SIZE):
        batch = paragraphs[start : start + EMBEDDING_BATCH_SIZE]
        batch_embeddings = paragraphs_to_embeddings(batch)
        all_embeddings.extend(batch_embeddings)
        end = start + len(batch)
        print(f"Embeddings {start + 1}-{end} are done!")

    return all_embeddings

def _get_all_paragraphs_lengths(paragraphs: List[str]) -> List[int]:
    lengths = []
    for paragraph in paragraphs:
        lengths.append(len(paragraph))

    return lengths

def chunk_10K(file_path: str, output_dir: Path | None = None) -> List[str]:
    ModelConfig.from_env().require_local_indexes()
    output_dir = output_dir if output_dir is not None else etl_pipeline.DATA_DIR
    with open(file_path, "r") as f:
        document = f.read()
        paragraphs = []
        for paragraph in _get_all_paragraphs(document):
            for start in range(0, len(paragraph), MAX_CHUNK_LENGTH):
                paragraphs.append(paragraph[start:start + MAX_CHUNK_LENGTH])
        paragraphs_lengths = _get_all_paragraphs_lengths(paragraphs)
        all_embeddings = _get_all_vector_embeddings(paragraphs)
        with open(output_dir / "all_embeddings.json", "w") as f2:
            json.dump(all_embeddings, f2)

        similarity_scores = []
        for i in range(len(all_embeddings)):
            if i + 1 < len(all_embeddings):
                score = get_similarity_score(all_embeddings[i], all_embeddings[i + 1])
                similarity_scores.append(score)

    all_chunks = []
    if not paragraphs:
        with open(output_dir / "all_chunks_embeddings.json", "w") as f:
            json.dump({"chunks": [], "embeddings": []}, f)
        return all_chunks

    current_chunk = paragraphs[0]
    current_chunk_length = paragraphs_lengths[0]
    for i in range(len(similarity_scores)):
        separator_length = len(CHUNK_SEPARATOR)
        fits_chunk_limit = current_chunk_length + separator_length + paragraphs_lengths[i + 1] <= MAX_CHUNK_LENGTH
        if similarity_scores[i] >= MERGE_SIMILARITY_THRESHOLD and fits_chunk_limit:
            current_chunk += CHUNK_SEPARATOR + paragraphs[i + 1]
            current_chunk_length += separator_length + paragraphs_lengths[i + 1]
        else:
            all_chunks.append(current_chunk)
            current_chunk = paragraphs[i + 1]
            current_chunk_length = paragraphs_lengths[i + 1]

    all_chunks.append(current_chunk)

    chunk_embeddings = _get_all_vector_embeddings(all_chunks)
    with open(output_dir / "all_chunks_embeddings.json", "w") as f:
        json.dump({"chunks": all_chunks, "embeddings": chunk_embeddings}, f)

    return all_chunks

if __name__ == "__main__":
    all_chunks = chunk_10K(str(etl_pipeline.DATA_DIR / "output_cleaner.txt"))

    with open(etl_pipeline.DATA_DIR / "all_chunks.txt", "w") as f:
        for chunk in all_chunks:
            f.write(chunk)
            f.write("\n\n")
            f.write("=============================================================")
            f.write("\n\n")
