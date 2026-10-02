"""Token-bounded semantic chunking for offline cloud preparation only."""

from etl_pipeline.chunker import CHUNK_SEPARATOR, MERGE_SIMILARITY_THRESHOLD
from etl_pipeline.cloud_cosine import cosine
from etl_pipeline.cloud_embeddings import embed
from etl_pipeline.cloud_tokens import BATCH_TEXTS, BATCH_TOKENS, CONTENT_TOKENS, token_count, tokenizer
from etl_pipeline.model_config import ModelConfig


def _split(paragraph: str) -> list[str]:
    pieces = []
    while paragraph:
        candidate = paragraph[:8000]
        encoding = tokenizer().encode(candidate, add_special_tokens=False)
        while len(encoding.ids) > CONTENT_TOKENS:
            candidate = candidate[:encoding.offsets[CONTENT_TOKENS][0]]
            encoding = tokenizer().encode(candidate, add_special_tokens=False)
        if not candidate:
            raise ValueError("Cannot split cloud embedding input without losing text")
        pieces.append(candidate)
        paragraph = paragraph[len(candidate):]
    return pieces


def _embeddings(texts: list[str], config: ModelConfig) -> list[list[float]]:
    vectors = []
    batch = []
    tokens = 0
    for text in texts:
        size = token_count(text)
        if batch and (len(batch) == BATCH_TEXTS or tokens + size > BATCH_TOKENS):
            vectors.extend(embed(batch, config))
            batch, tokens = [], 0
        batch.append(text)
        tokens += size
    if batch:
        vectors.extend(embed(batch, config))
    return vectors


def chunk_document(document: str, config: ModelConfig) -> tuple[list[str], list[list[float]]]:
    if config.runtime != "cloud":
        raise ValueError("Cloud chunking requires the cloud profile")
    paragraphs = [piece for paragraph in document.split("\n\n") if paragraph.strip() for piece in _split(paragraph)]
    if not paragraphs:
        raise ValueError("Cannot index an empty cloud document")
    vectors = _embeddings(paragraphs, config)
    chunks = []
    current = paragraphs[0]
    for position, following in enumerate(paragraphs[1:]):
        combined = current + CHUNK_SEPARATOR + following
        similar = cosine(vectors[position], vectors[position + 1]) >= MERGE_SIMILARITY_THRESHOLD
        if similar and len(combined) <= 8000 and token_count(combined, special_tokens=False) <= CONTENT_TOKENS:
            current = combined
        else:
            chunks.append(current)
            current = following
    chunks.append(current)
    return chunks, _embeddings(chunks, config)
