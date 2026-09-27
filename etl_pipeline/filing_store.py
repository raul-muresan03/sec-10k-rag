"""Resolve verified, filing-scoped indexes from the dev corpus."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

import etl_pipeline
from etl_pipeline.chunker import EMBEDDING_MODEL
from etl_pipeline.embedding_model import embedding_model_digest
from etl_pipeline.filings import MANIFEST_PATH, VerifiedFiling, filing_id, hash_file, verify_filings
from etl_pipeline.indexing import INDEX_FILENAME, index_configuration
from etl_pipeline.vector_store import load_index


METADATA_FILENAME = "filing.json"


@dataclass(frozen=True)
class PreparedFiling:
    filing_id: str
    ticker: str
    year: int
    accession: str
    sec_url: str
    index_version: str
    index_path: Path
    index_sha256: str
    chunk_count: int


def _version(filing: VerifiedFiling, config: dict) -> str:
    payload = json.dumps({"source_sha256": filing.sha256, "index_configuration": config}, sort_keys=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def _configuration() -> dict:
    return index_configuration(embedding_model_digest(EMBEDDING_MODEL))


class FilingIndexStore:
    def __init__(self, manifest_path: Path = MANIFEST_PATH, index_root: Path | None = None):
        self.manifest_path = manifest_path
        self.index_root = index_root if index_root is not None else etl_pipeline.DATA_DIR / "indexes"

    def dev_filings(self) -> tuple[str, dict[tuple[str, int], VerifiedFiling]]:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not isinstance(manifest.get("filings"), list):
            raise ValueError("Invalid corpus manifest")
        keys = set()
        for entry in manifest["filings"]:
            if not isinstance(entry, dict):
                raise ValueError("Invalid filing in corpus manifest")
            if entry.get("split") == "dev":
                try:
                    keys.add((entry["ticker"], entry["filing_year"]))
                except KeyError as error:
                    raise ValueError(f"Missing manifest field: {error.args[0]}") from error
        _, digest, filings = verify_filings(self.manifest_path, keys, "dev")
        if not filings:
            raise ValueError("No dev filings in corpus manifest")
        for filing in filings.values():
            filing_id(filing)
        return digest, dict(sorted(filings.items()))

    def verified(self, ticker: str, year: int) -> tuple[str, VerifiedFiling]:
        key = (ticker.strip().upper(), year)
        _, digest, filings = verify_filings(self.manifest_path, {key}, "dev")
        filing = filings[key]
        filing_id(filing)
        return digest, filing

    def _directory(self, filing: VerifiedFiling, config: dict) -> Path:
        return self.index_root / filing_id(filing) / _version(filing, config)

    def _load(self, filing: VerifiedFiling, config: dict) -> PreparedFiling | None:
        directory = self._directory(filing, config)
        if not directory.exists():
            return None
        metadata = json.loads((directory / METADATA_FILENAME).read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError(f"Invalid index metadata for {filing.ticker} {filing.year}")
        expected = {
            "schema_version": 1, "filing_id": filing_id(filing), "ticker": filing.ticker,
            "filing_year": filing.year, "accession": filing.accession, "sec_url": filing.sec_url,
            "source_sha256": filing.sha256, "index_version": directory.name,
            "index_configuration": config,
        }
        if any(metadata.get(key) != value for key, value in expected.items()):
            raise ValueError(f"Index metadata does not match {filing.ticker} {filing.year}")
        path = directory / INDEX_FILENAME
        if metadata.get("index_sha256") != hash_file(path):
            raise ValueError(f"Index SHA-256 mismatch for {filing.ticker} {filing.year}")
        chunks, _ = load_index(path)
        if metadata.get("chunk_count") != len(chunks):
            raise ValueError(f"Index chunk count mismatch for {filing.ticker} {filing.year}")
        return PreparedFiling(
            filing_id(filing), filing.ticker, filing.year, filing.accession, filing.sec_url or "",
            directory.name, path, metadata["index_sha256"], len(chunks),
        )

    def prepared(self) -> list[PreparedFiling]:
        _, filings = self.dev_filings()
        config = _configuration()
        return [ready for filing in filings.values() if (ready := self._load(filing, config)) is not None]

    def resolve(self, ticker: str, year: int) -> PreparedFiling:
        _, filing = self.verified(ticker, year)
        ready = self._load(filing, _configuration())
        if ready is None:
            raise RuntimeError(f"Index not prepared for {ticker} {year}; run python -m etl_pipeline.filing_store")
        return ready
