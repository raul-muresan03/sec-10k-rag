"""Build filing indexes with explicit output paths."""

from pathlib import Path

from etl_pipeline.chunker import (
    CHUNK_SEPARATOR, EMBEDDING_BATCH_SIZE, EMBEDDING_MODEL,
    MAX_CHUNK_LENGTH, MERGE_SIMILARITY_THRESHOLD, chunk_10K,
)
from etl_pipeline.cleaner import clean_10K
from etl_pipeline.filings import VerifiedFiling, hash_file
from etl_pipeline.parser import parse_10K
from etl_pipeline.vector_store import load_index
from etl_pipeline.model_config import ModelConfig


INDEX_SOURCE_FILES = ("parser.py", "cleaner.py", "chunker.py", "indexing.py", "vector_store.py")
INDEX_FILENAME = "all_chunks_embeddings.json"


def index_configuration(embedding_digest: str | None = None) -> dict:
    pipeline_dir = Path(__file__).parent
    return {
        "embedding_model": {"tag": EMBEDDING_MODEL, "digest": embedding_digest},
        "chunker": {
            "max_chunk_length": MAX_CHUNK_LENGTH,
            "separator": CHUNK_SEPARATOR,
            "merge_similarity_threshold": MERGE_SIMILARITY_THRESHOLD,
            "embedding_batch_size": EMBEDDING_BATCH_SIZE,
        },
        "source_sha256": {name: hash_file(pipeline_dir / name) for name in INDEX_SOURCE_FILES},
    }


def build_index(filing: VerifiedFiling, directory: Path) -> dict:
    """Build from a verified filing in a caller-owned empty directory."""
    ModelConfig.from_env().require_local_indexes()
    if hash_file(filing.path) != filing.sha256:
        raise ValueError(f"Filing changed before indexing: {filing.path}")
    parsed = directory / "output_parser.txt"
    cleaned = directory / "output_cleaner.txt"
    parse_10K(str(filing.path), output_path=parsed)
    clean_10K(str(parsed), output_path=cleaned)
    chunk_10K(str(cleaned), output_dir=directory)
    index_path = directory / INDEX_FILENAME
    if not index_path.is_file():
        raise RuntimeError(f"Index not created for {filing.ticker} {filing.year}: {index_path}")
    chunks, _ = load_index(index_path)
    if hash_file(filing.path) != filing.sha256:
        raise ValueError(f"Filing changed during indexing: {filing.path}")
    return {
        "strategy": "rebuilt_from_verified_filing_in_temporary_directory",
        "sha256": hash_file(index_path),
        "chunk_count": len(chunks),
    }
