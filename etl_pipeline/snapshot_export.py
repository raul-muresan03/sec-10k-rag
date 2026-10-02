"""Deterministic publication of verified cloud indexes into a new directory."""

import gzip
from hashlib import sha256
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import os

from etl_pipeline.cloud_identity import canonical_json, configuration_id, embedding_configuration
from etl_pipeline.filings import VerifiedFiling, filing_id, hash_file
from etl_pipeline.runtime_snapshot import SnapshotStore
from etl_pipeline.vector_store import load_index
from etl_pipeline.snapshot_provenance import verify_index_metadata


def export_snapshot(filings: list[tuple[VerifiedFiling, Path]], config: dict,
                    corpus_sha256: str, destination: Path) -> None:
    if destination.exists():
        raise ValueError("Snapshot destination already exists; publish into a new directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    config_id = configuration_id(config)
    manifest = {
        "schema_version": 1, "embedding_configuration": embedding_configuration(),
        "embedding_config_id": configuration_id(embedding_configuration()),
        "index_configuration": config, "index_config_id": config_id,
        "corpus_manifest_sha256": corpus_sha256, "filings": [],
    }
    with TemporaryDirectory(prefix=".snapshot-", dir=destination.parent) as temporary:
        workspace = Path(temporary)
        for filing, index_path in sorted(filings, key=lambda pair: (pair[0].ticker, pair[0].year)):
            if filing.split != "dev" or hash_file(filing.path) != filing.sha256:
                raise ValueError("Export requires unchanged verified dev filings")
            verify_index_metadata(filing, index_path, config)
            chunks, vectors = load_index(index_path)
            expanded = canonical_json({"chunks": chunks, "embeddings": vectors})
            stream = io.BytesIO()
            with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as archive:
                archive.write(expanded)
            compressed = stream.getvalue()
            selected_id = filing_id(filing)
            filename = selected_id + ".json.gz"
            (workspace / filename).write_bytes(compressed)
            manifest["filings"].append({
                "filing_id": selected_id, "ticker": filing.ticker, "filing_year": filing.year,
                "split": "dev", "accession": filing.accession, "sec_url": filing.sec_url,
                "source_sha256": filing.sha256,
                "index_version": configuration_id({"source_sha256": filing.sha256, "index_config_id": config_id}),
                "filename": filename, "sha256": sha256(compressed).hexdigest(), "chunk_count": len(chunks),
                "compressed_bytes": len(compressed), "expanded_bytes": len(expanded),
            })
        manifest["snapshot_id"] = configuration_id(manifest)
        (workspace / "manifest.json").write_bytes(canonical_json(manifest) + b"\n")
        SnapshotStore(workspace)
        for path in workspace.iterdir():
            path.chmod(0o644)
        workspace.chmod(0o755)
        os.rename(workspace, destination)
