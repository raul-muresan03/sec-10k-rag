"""Embedding-space identity and offline indexing provenance, without secrets."""

from hashlib import sha256
import json
from math import hypot, isfinite
from pathlib import Path

from etl_pipeline.chunker import CHUNK_SEPARATOR, MERGE_SIMILARITY_THRESHOLD
from etl_pipeline.cloud_tokens import (
    BATCH_TEXTS, BATCH_TOKENS, CONTENT_TOKENS, INPUT_TOKENS, QUERY_PREFIX, TOKENIZER_REVISION, TOKENIZER_SHA256,
)
from etl_pipeline.filings import hash_file
from etl_pipeline.model_config import CLOUD_EMBEDDING_DIMENSION, CLOUD_EMBEDDING_MODEL


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def configuration_id(value: object) -> str:
    return sha256(canonical_json(value)).hexdigest()


def embedding_configuration() -> dict:
    return {
        "provider": "cloudflare", "model": CLOUD_EMBEDDING_MODEL, "revision": None,
        "dimension": CLOUD_EMBEDDING_DIMENSION, "pooling": "mean", "normalization": "provider_passthrough",
        "document_prefix": "", "query_prefix": QUERY_PREFIX,
        "tokenizer": {"model": "BAAI/bge-small-en-v1.5", "revision": TOKENIZER_REVISION,
                      "sha256": TOKENIZER_SHA256, "implementation": "tokenizers/0.23.2", "truncation": False},
        "content_tokens": CONTENT_TOKENS, "input_tokens": INPUT_TOKENS,
    }


def index_configuration() -> dict:
    names = ("parser.py", "cleaner.py", "chunker.py", "cloud_chunker.py", "cloud_embeddings.py",
             "cloud_tokens.py", "cloud_cosine.py", "cloud_identity.py", "cloud_indexing.py")
    return {
        "embedding": embedding_configuration(),
        "chunking": {"strategy": "token_bounded_adjacent_cosine", "separator": CHUNK_SEPARATOR,
                     "merge_similarity_threshold": MERGE_SIMILARITY_THRESHOLD, "max_characters": 8000,
                     "batch_texts": BATCH_TEXTS, "batch_tokens": BATCH_TOKENS},
        "source_sha256": {name: hash_file(Path(__file__).parent / name) for name in names},
        "model_identity_note": "Cloudflare exposes no immutable weight/tokenizer revision; export hashes freeze data.",
    }


def valid_vector(vector: object) -> bool:
    try:
        return (
            isinstance(vector, list) and len(vector) == CLOUD_EMBEDDING_DIMENSION
            and all(type(value) in (int, float) and isfinite(value) for value in vector)
            and 0 < hypot(*vector) < float("inf")
        )
    except OverflowError:
        return False
