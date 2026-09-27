"""Verify frozen SEC inputs and build isolated, filing-scoped evaluation indexes."""

from contextlib import contextmanager
import json
from pathlib import Path
from typing import Iterator

import etl_pipeline
from etl_pipeline.chunker import (
    CHUNK_SEPARATOR, EMBEDDING_BATCH_SIZE, EMBEDDING_MODEL,
    MAX_CHUNK_LENGTH, MERGE_SIMILARITY_THRESHOLD, chunk_10K,
)
from etl_pipeline.cleaner import clean_10K
from etl_pipeline.filings import MANIFEST_PATH, VerifiedFiling, hash_file, verify_filings
from etl_pipeline.parser import parse_10K


INDEX_SOURCE_FILES = ("parser.py", "cleaner.py", "chunker.py", "vector_store.py")


@contextmanager
def use_index_directory(path: Path) -> Iterator[None]:
    previous = etl_pipeline.DATA_DIR
    etl_pipeline.DATA_DIR = path
    try:
        yield
    finally:
        etl_pipeline.DATA_DIR = previous


def build_index(filing: VerifiedFiling, directory: Path) -> dict:
    """Rebuild the index from a verified filing; caller supplies an empty directory."""
    if hash_file(filing.path) != filing.sha256:
        raise ValueError(f"Filing changed before indexing: {filing.path}")
    parse_10K(str(filing.path))
    clean_10K(str(directory / "output_parser.txt"))
    chunk_10K(str(directory / "output_cleaner.txt"))
    index_path = directory / "all_chunks_embeddings.json"
    if not index_path.is_file():
        raise RuntimeError(f"Index not created for {filing.ticker} {filing.year}: {index_path}")
    index_hash = hash_file(index_path)
    with index_path.open(encoding="utf-8") as source:
        index = json.load(source)
    if (
        not isinstance(index, dict)
        or not isinstance(index.get("chunks"), list)
        or not isinstance(index.get("embeddings"), list)
    ):
        raise ValueError(f"Invalid index for {filing.ticker} {filing.year}")
    if not index["chunks"] or len(index["chunks"]) != len(index["embeddings"]):
        raise ValueError(f"Index chunk/embedding count mismatch for {filing.ticker} {filing.year}")
    if hash_file(filing.path) != filing.sha256:
        raise ValueError(f"Filing changed during indexing: {filing.path}")
    return {
        "strategy": "rebuilt_from_verified_filing_in_temporary_directory",
        "sha256": index_hash,
        "chunk_count": len(index["chunks"]),
    }


def index_configuration() -> dict:
    pipeline_dir = Path(etl_pipeline.__file__).parent
    return {
        "embedding_model": {"tag": EMBEDDING_MODEL, "digest": None},
        "chunker": {
            "max_chunk_length": MAX_CHUNK_LENGTH,
            "separator": CHUNK_SEPARATOR,
            "merge_similarity_threshold": MERGE_SIMILARITY_THRESHOLD,
            "embedding_batch_size": EMBEDDING_BATCH_SIZE,
        },
        "source_sha256": {name: hash_file(pipeline_dir / name) for name in INDEX_SOURCE_FILES},
    }
