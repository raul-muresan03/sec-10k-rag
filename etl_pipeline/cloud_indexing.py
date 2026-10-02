"""Operator-only cloud indexing in a separate cache; never touches local indexes."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import os

import etl_pipeline
from etl_pipeline.cleaner import clean_10K
from etl_pipeline.cloud_chunker import chunk_document
from etl_pipeline.cloud_identity import canonical_json, configuration_id, index_configuration
from etl_pipeline.filings import MANIFEST_PATH, VerifiedFiling, catalog_filings, hash_file, verify_filings
from etl_pipeline.model_config import ModelConfig
from etl_pipeline.parser import parse_10K
from etl_pipeline.runtime_snapshot import SnapshotStore
from etl_pipeline.snapshot_export import export_snapshot
from etl_pipeline.vector_store import load_index


def _index_path(filing: VerifiedFiling, root: Path, identity: dict) -> Path:
    version = configuration_id({"source_sha256": filing.sha256, "configuration": identity})
    return root / filing.ticker / version / "index.json"


def _prepare(filing: VerifiedFiling, root: Path, config: ModelConfig, identity: dict) -> None:
    path = _index_path(filing, root, identity)
    directory, version = path.parent, path.parent.name
    if directory.exists():
        metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        if metadata != {"version": version, "sha256": hash_file(path)}:
            raise ValueError("Cloud index cache checksum mismatch")
        load_index(path)
        return
    directory.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".cloud-", dir=directory.parent) as temporary:
        workspace = Path(temporary)
        parsed, cleaned = workspace / "parsed.txt", workspace / "cleaned.txt"
        parse_10K(str(filing.path), output_path=parsed)
        clean_10K(str(parsed), output_path=cleaned)
        chunks, vectors = chunk_document(cleaned.read_text(encoding="utf-8"), config)
        output = workspace / "index.json"
        output.write_bytes(canonical_json({"chunks": chunks, "embeddings": vectors}))
        if hash_file(filing.path) != filing.sha256 or identity != index_configuration():
            raise ValueError("Cloud indexing source or configuration changed during preparation")
        metadata = {"version": version, "sha256": hash_file(output)}
        (workspace / "metadata.json").write_bytes(canonical_json(metadata))
        parsed.unlink()
        cleaned.unlink()
        os.rename(workspace, directory)


def prepare_snapshot(manifest_path: Path, index_root: Path, destination: Path, config: ModelConfig,
                     *, selected: set[tuple[str, int]] | None = None) -> None:
    if config.runtime != "cloud":
        raise ValueError("Cloud preparation requires the explicit cloud profile")
    catalog = catalog_filings(manifest_path)
    keys = selected if selected is not None else {(filing.ticker, filing.year) for filing in catalog.values()}
    _, manifest_hash, verified = verify_filings(manifest_path, keys, "dev")
    identity = index_configuration()
    indexes = []
    for filing in verified.values():
        _prepare(filing, index_root, config, identity)
        indexes.append((filing, _index_path(filing, index_root, identity)))
    if hash_file(manifest_path) != manifest_hash:
        raise ValueError("Corpus manifest changed during cloud preparation")
    export_snapshot(indexes, identity, manifest_hash, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a new immutable cloud dev snapshot offline.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--index-root", type=Path, default=etl_pipeline.DATA_DIR / "cloud-indexes")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ticker")
    parser.add_argument("--year", type=int)
    args = parser.parse_args()
    if (args.ticker is None) != (args.year is None):
        parser.error("--ticker and --year must be supplied together")
    try:
        selected = {(args.ticker.upper(), args.year)} if args.ticker is not None else None
        prepare_snapshot(args.manifest, args.index_root, args.output, ModelConfig.from_env(), selected=selected)
        store = SnapshotStore(args.output)
        print("Snapshot:", store.snapshot_id)
        for item in store.prepared():
            print(item.ticker, item.year, item.chunk_count, "chunks")
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
