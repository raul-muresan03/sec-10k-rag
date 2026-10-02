"""Bounded, checksummed JSON/gzip format shared by exporter and runtime reader."""

import gzip
from hashlib import sha256
import io
import json
from pathlib import Path
import re

from etl_pipeline.cloud_identity import configuration_id, embedding_configuration, valid_vector
from etl_pipeline.cloud_tokens import validated_input
from etl_pipeline.filings import VerifiedFiling, filing_id


MAX_MANIFEST_BYTES = 128 * 1024
MAX_COMPRESSED_BYTES = 32 * 1024 * 1024
MAX_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_TOTAL_COMPRESSED_BYTES = 128 * 1024 * 1024
MAX_TOTAL_EXPANDED_BYTES = 256 * 1024 * 1024
DEFAULT_SNAPSHOT_ROOT = Path(__file__).resolve().parents[1] / "deploy" / "indexes"


def read_bounded(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Snapshot file is missing, linked, or exceeds the size limit")
    with path.open("rb") as source:
        content = source.read(limit + 1)
    if len(content) > limit:
        raise ValueError("Snapshot file exceeds the size limit")
    return content


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Snapshot JSON contains duplicate keys")
        result[key] = value
    return result


def parse_json(content: bytes) -> dict:
    try:
        result = json.loads(content, object_pairs_hook=_no_duplicate_keys)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("Invalid snapshot JSON") from None
    if not isinstance(result, dict):
        raise ValueError("Snapshot JSON must be an object")
    return result


def valid_hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def validate_manifest(manifest: dict) -> None:
    fields = {"schema_version", "snapshot_id", "embedding_configuration", "embedding_config_id",
              "index_configuration", "index_config_id", "corpus_manifest_sha256", "filings"}
    if set(manifest) != fields or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("Invalid snapshot manifest schema")
    if manifest["embedding_configuration"] != embedding_configuration():
        raise ValueError("Incompatible snapshot embedding configuration")
    if manifest["embedding_config_id"] != configuration_id(manifest["embedding_configuration"]):
        raise ValueError("Snapshot embedding configuration checksum mismatch")
    config = manifest["index_configuration"]
    if (not isinstance(config, dict) or config.get("embedding") != manifest["embedding_configuration"]
            or manifest["index_config_id"] != configuration_id(config)):
        raise ValueError("Invalid snapshot indexing provenance")
    hashes = config.get("source_sha256")
    if not isinstance(hashes, dict) or not hashes or any(
        not isinstance(name, str) or not re.fullmatch(r"[a-z_]+\.py", name) or not valid_hash(value)
        for name, value in hashes.items()
    ):
        raise ValueError("Missing snapshot indexing source hashes")
    if not valid_hash(manifest["corpus_manifest_sha256"]):
        raise ValueError("Invalid snapshot corpus checksum")
    payload = {key: value for key, value in manifest.items() if key != "snapshot_id"}
    if manifest["snapshot_id"] != configuration_id(payload):
        raise ValueError("Snapshot manifest checksum mismatch")
    entries = manifest["filings"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 6:
        raise ValueError("Snapshot must contain one to six dev filings")
    ids, keys = set(), set()
    compressed, expanded = 0, 0
    for entry in entries:
        validate_entry(entry, manifest["index_config_id"])
        key = (entry["ticker"], entry["filing_year"])
        if entry["filing_id"] in ids or key in keys:
            raise ValueError("Duplicate snapshot filing identity")
        ids.add(entry["filing_id"])
        keys.add(key)
        compressed += entry["compressed_bytes"]
        expanded += entry["expanded_bytes"]
    if compressed > MAX_TOTAL_COMPRESSED_BYTES or expanded > MAX_TOTAL_EXPANDED_BYTES:
        raise ValueError("Snapshot total size exceeds the limit")


def validate_entry(entry: object, index_config_id: str) -> None:
    fields = {"filing_id", "ticker", "filing_year", "split", "accession", "sec_url", "source_sha256",
              "index_version", "filename", "sha256", "chunk_count", "compressed_bytes", "expanded_bytes"}
    if not isinstance(entry, dict) or set(entry) != fields or entry["split"] != "dev":
        raise ValueError("Invalid dev snapshot filing schema")
    if (not isinstance(entry["ticker"], str) or not re.fullmatch(r"[A-Z]{1,10}", entry["ticker"])
            or type(entry["filing_year"]) is not int or not 1993 <= entry["filing_year"] <= 2100
            or not isinstance(entry["accession"], str) or not isinstance(entry["sec_url"], str)):
        raise ValueError("Invalid snapshot company identity")
    filing = VerifiedFiling(entry["ticker"], entry["filing_year"], "dev", entry["accession"],
                            Path("."), entry["source_sha256"], entry["sec_url"])
    selected_id = filing_id(filing)
    if entry["filing_id"] != selected_id or entry["filename"] != selected_id + ".json.gz":
        raise ValueError("Invalid snapshot filing identity or filename")
    if any(not valid_hash(entry[key]) for key in ("source_sha256", "sha256", "index_version")):
        raise ValueError("Invalid snapshot filing checksum")
    version = configuration_id({"source_sha256": entry["source_sha256"], "index_config_id": index_config_id})
    if entry["index_version"] != version:
        raise ValueError("Snapshot index version mismatch")
    for key, limit in (("chunk_count", 100_000), ("compressed_bytes", MAX_COMPRESSED_BYTES),
                       ("expanded_bytes", MAX_EXPANDED_BYTES)):
        if type(entry[key]) is not int or not 1 <= entry[key] <= limit:
            raise ValueError("Invalid snapshot filing count or size")


def read_index(root: Path, entry: dict) -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...]]:
    content = read_bounded(root / entry["filename"], MAX_COMPRESSED_BYTES)
    if len(content) != entry["compressed_bytes"] or sha256(content).hexdigest() != entry["sha256"]:
        raise ValueError("Snapshot compressed index checksum mismatch")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(content)) as source:
            expanded = source.read(entry["expanded_bytes"] + 1)
    except (OSError, EOFError):
        raise ValueError("Invalid snapshot gzip index") from None
    if len(expanded) != entry["expanded_bytes"]:
        raise ValueError("Snapshot expanded index size mismatch")
    index = parse_json(expanded)
    if set(index) != {"chunks", "embeddings"}:
        raise ValueError("Invalid snapshot index schema")
    chunks, vectors = index["chunks"], index["embeddings"]
    if (not isinstance(chunks, list) or not isinstance(vectors, list)
            or len(chunks) != entry["chunk_count"] or len(chunks) != len(vectors)
            or any(not valid_vector(vector) for vector in vectors)):
        raise ValueError("Invalid snapshot vector dimensions, values, norms, or counts")
    for text in chunks:
        validated_input(text)
    return tuple(chunks), tuple(tuple(vector) for vector in vectors)
