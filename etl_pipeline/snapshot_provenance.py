"""Mandatory indexing provenance and bindings between source, configuration and vectors."""

from math import isfinite
from pathlib import Path
import re

from etl_pipeline.cloud_identity import configuration_id
from etl_pipeline.filings import VerifiedFiling, hash_file


REQUIRED_SOURCE_FILES = {
    "parser.py", "cleaner.py", "chunker.py", "cloud_chunker.py", "cloud_embeddings.py",
    "cloud_tokens.py", "cloud_cosine.py", "cloud_identity.py", "cloud_indexing.py",
}


def validate_provenance(config: dict) -> None:
    if set(config) != {"embedding", "chunking", "source_sha256", "model_identity_note"}:
        raise ValueError("Incomplete snapshot indexing provenance")
    hashes = config["source_sha256"]
    if (not isinstance(hashes, dict) or set(hashes) != REQUIRED_SOURCE_FILES
            or any(not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value)
                   for value in hashes.values())):
        raise ValueError("Incomplete snapshot source provenance")
    chunking = config["chunking"]
    fields = {"strategy", "separator", "merge_similarity_threshold", "max_characters", "batch_texts", "batch_tokens"}
    if not isinstance(chunking, dict) or set(chunking) != fields:
        raise ValueError("Incomplete snapshot chunking provenance")
    if chunking["strategy"] != "token_bounded_adjacent_cosine" or chunking["separator"] != " ":
        raise ValueError("Unsupported snapshot chunking provenance")
    threshold = chunking["merge_similarity_threshold"]
    if type(threshold) not in (int, float) or not -1 <= threshold <= 1 or not isfinite(threshold):
        raise ValueError("Invalid snapshot similarity provenance")
    for key, limit in (("max_characters", 8000), ("batch_texts", 100), ("batch_tokens", 8192)):
        if type(chunking[key]) is not int or not 1 <= chunking[key] <= limit:
            raise ValueError("Invalid snapshot chunking bounds provenance")
    note = config["model_identity_note"]
    if not isinstance(note, str) or not 1 <= len(note) <= 1024:
        raise ValueError("Missing snapshot model identity provenance")


def verify_index_metadata(filing: VerifiedFiling, path: Path, config: dict) -> None:
    from etl_pipeline.snapshot_format import MAX_MANIFEST_BYTES, parse_json, read_bounded

    metadata_path = path.parent / "metadata.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("Cloud index metadata requires a regular index file")
    try:
        metadata = parse_json(read_bounded(metadata_path, MAX_MANIFEST_BYTES))
    except (OSError, ValueError):
        raise ValueError("Cloud index metadata is missing or invalid") from None
    expected = {
        "version": configuration_id({"source_sha256": filing.sha256, "configuration": config}),
        "sha256": hash_file(path),
    }
    if metadata != expected or path.name != "index.json" or path.parent.name != expected["version"]:
        raise ValueError("Cloud index metadata does not bind the selected filing and embedding configuration")
