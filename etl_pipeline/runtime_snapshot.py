"""Read-only runtime catalog independent of raw filings, Ollama and preparation."""

from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
import os
from typing import Protocol

from etl_pipeline.snapshot_format import (
    DEFAULT_SNAPSHOT_ROOT, MAX_MANIFEST_BYTES, parse_json, read_bounded, read_index, validate_manifest,
)


@dataclass(frozen=True)
class SnapshotFiling:
    filing_id: str
    ticker: str
    year: int
    accession: str
    sec_url: str
    index_version: str
    index_path: Path
    index_sha256: str
    chunk_count: int
    source_sha256: str


class FilingReference(Protocol):
    """Filing identity used by retrieval and evaluation."""

    @property
    def filing_id(self) -> str:
        ...

    @property
    def ticker(self) -> str:
        ...

    @property
    def year(self) -> int:
        ...

    @property
    def source_sha256(self) -> str:
        ...


class SnapshotReader(Protocol):
    """Verified filing vectors behind a manifest; implemented by exports and frozen test indexes."""

    @property
    def snapshot_id(self) -> str:
        ...

    @property
    def embedding_config_id(self) -> str:
        ...

    @property
    def manifest(self) -> dict:
        ...

    def index(self, selected_id: str) -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...]]:
        ...

    def resolve(self, ticker: str, year: int) -> FilingReference:
        ...


class SnapshotStore:
    def __init__(self, root: Path = DEFAULT_SNAPSHOT_ROOT):
        self.root = root
        manifest = parse_json(read_bounded(root / "manifest.json", MAX_MANIFEST_BYTES))
        validate_manifest(manifest)
        self.snapshot_id = manifest["snapshot_id"]
        self.embedding_config_id = manifest["embedding_config_id"]
        self._manifest = manifest
        self._filings = {}
        self._indexes = {}
        for entry in manifest["filings"]:
            item = SnapshotFiling(
                entry["filing_id"], entry["ticker"], entry["filing_year"], entry["accession"], entry["sec_url"],
                entry["index_version"], root / entry["filename"], entry["sha256"], entry["chunk_count"],
                entry["source_sha256"],
            )
            self._indexes[item.filing_id] = read_index(root, entry)
            self._filings[item.filing_id] = item

    @classmethod
    def from_env(cls) -> "SnapshotStore":
        return cls(Path(os.getenv("RAG_SNAPSHOT_DIR", str(DEFAULT_SNAPSHOT_ROOT))))

    @property
    def manifest(self) -> dict:
        return deepcopy(self._manifest)

    def catalog(self) -> dict[str, SnapshotFiling]:
        return dict(self._filings)

    def prepared(self) -> list[SnapshotFiling]:
        return list(self._filings.values())

    def resolve_id(self, selected_id: str) -> SnapshotFiling:
        return self._filings[selected_id]

    def resolve(self, ticker: str, year: int) -> SnapshotFiling:
        for item in self._filings.values():
            if (item.ticker, item.year) == (ticker.strip().upper(), year):
                return item
        raise KeyError("Unknown snapshot filing")

    def index(self, selected_id: str) -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...]]:
        return self._indexes[selected_id]
