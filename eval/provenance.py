"""Verify frozen SEC inputs and build isolated, filing-scoped evaluation indexes."""

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Iterator

import etl_pipeline
from etl_pipeline.chunker import (
    CHUNK_SEPARATOR, EMBEDDING_BATCH_SIZE, EMBEDDING_MODEL,
    MAX_CHUNK_LENGTH, MERGE_SIMILARITY_THRESHOLD, chunk_10K,
)
from etl_pipeline.cleaner import clean_10K
from etl_pipeline.parser import parse_10K


MANIFEST_PATH = Path(__file__).with_name("corpus_manifest.v1.json")
INDEX_SOURCE_FILES = ("parser.py", "cleaner.py", "chunker.py", "vector_store.py")


@dataclass(frozen=True)
class VerifiedFiling:
    ticker: str
    year: int
    split: str
    accession: str
    path: Path
    sha256: str


def hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_filings(
    manifest_path: Path, keys: set[tuple[str, int]], split: str,
) -> tuple[int, str, dict[tuple[str, int], VerifiedFiling]]:
    manifest_path = manifest_path.resolve()
    manifest_hash = hash_file(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or type(manifest.get("version")) is not int
        or manifest["version"] != 1
        or not isinstance(manifest.get("filings"), list)
    ):
        raise ValueError(f"Invalid v1 corpus manifest: {manifest_path}")

    root = manifest_path.parent.parent
    selected = {}
    for entry in manifest["filings"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid filing in corpus manifest")
        try:
            ticker, year = entry["ticker"], entry["filing_year"]
            accession, entry_split = entry["accession"], entry["split"]
            relative_path, expected_hash = entry["path"], entry["sha256"]
        except KeyError as error:
            raise ValueError(f"Missing manifest field: {error.args[0]}") from error
        if not isinstance(ticker, str) or type(year) is not int:
            raise ValueError("Invalid ticker/year in corpus manifest")
        key = (ticker, year)
        if key not in keys:
            continue
        if key in selected:
            raise ValueError(f"Duplicate filing in corpus manifest: {key}")
        if entry_split != split:
            raise ValueError(f"Split mismatch for {ticker} {year}: manifest has {entry_split}, expected {split}")
        expected_path = f"data/sec-edgar-filings/{ticker}/10-K/{accession}/full-submission.txt"
        if (
            not isinstance(accession, str)
            or relative_path != expected_path
            or not isinstance(expected_hash, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
        ):
            raise ValueError(f"Invalid accession/path/hash in manifest for {ticker} {year}")
        path = root / relative_path
        if not path.is_file():
            raise ValueError(f"Filing missing for {ticker} {year}: {path}")
        if hash_file(path) != expected_hash:
            raise ValueError(f"Filing SHA-256 mismatch for {ticker} {year}: {path}")
        with path.open("r", encoding="utf-8", errors="replace") as source:
            header = source.read(16_384)
        fields = {
            label: re.search(rf"^{label}:\s*([^\r\n]+)", header, flags=re.MULTILINE)
            for label in ("ACCESSION NUMBER", "CONFORMED SUBMISSION TYPE", "FILED AS OF DATE")
        }
        if (
            any(match is None for match in fields.values())
            or fields["ACCESSION NUMBER"].group(1).strip() != accession
            or fields["CONFORMED SUBMISSION TYPE"].group(1).strip() != "10-K"
            or fields["FILED AS OF DATE"].group(1).strip()[:4] != str(year)
        ):
            raise ValueError(f"SEC header accession/form/filing year mismatch for {ticker} {year}: {path}")
        selected[key] = VerifiedFiling(ticker, year, split, accession, path, expected_hash)

    missing = keys - selected.keys()
    if missing:
        raise ValueError(f"No manifest filing for: {sorted(missing)}")
    if hash_file(manifest_path) != manifest_hash:
        raise ValueError(f"Corpus manifest changed while verifying: {manifest_path}")
    return manifest["version"], manifest_hash, selected


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
