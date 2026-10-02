"""Resolve verified, filing-scoped indexes from the dev corpus."""

import argparse
from dataclasses import dataclass
import errno
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import etl_pipeline
from etl_pipeline.chunker import EMBEDDING_MODEL
from etl_pipeline.embedding_model import embedding_model_digest
from etl_pipeline.filings import (
    MANIFEST_PATH, SEC_URL, VerifiedFiling, catalog_filings, filing_id, hash_file, verify_filings,
)
from etl_pipeline.indexing import INDEX_FILENAME, build_index, index_configuration
from etl_pipeline.vector_store import load_index
from etl_pipeline.model_config import ModelConfig


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
        ModelConfig.from_env().require_local_indexes()
        self.manifest_path = manifest_path
        self.index_root = index_root if index_root is not None else etl_pipeline.DATA_DIR / "indexes"

    def catalog(self) -> dict[str, VerifiedFiling]:
        return catalog_filings(self.manifest_path)

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
        available = []
        config = None
        for filing in self.catalog().values():
            if not filing.path.is_file():
                continue
            try:
                _, verified = self.verified(filing.ticker, filing.year)
                if config is None:
                    config = _configuration()
                ready = self._load(verified, config)
            except (OSError, ValueError):
                continue
            if ready is not None:
                available.append(ready)
        return available

    def resolve(self, ticker: str, year: int) -> PreparedFiling:
        _, filing = self.verified(ticker, year)
        ready = self._load(filing, _configuration())
        if ready is None:
            raise RuntimeError(f"Index not prepared for {ticker} {year}; run python -m etl_pipeline.filing_store")
        return ready

    def resolve_id(self, selected_id: str) -> PreparedFiling:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not isinstance(manifest.get("filings"), list):
            raise ValueError("Invalid corpus manifest")
        for entry in manifest["filings"]:
            if not isinstance(entry, dict) or entry.get("split") != "dev":
                continue
            url = entry.get("sec_url")
            match = SEC_URL.fullmatch(url) if isinstance(url, str) else None
            if match is None or selected_id != f"{match['cik']}-{entry.get('accession')}":
                continue
            ready = self.resolve(entry["ticker"], entry["filing_year"])
            if ready.filing_id != selected_id:
                raise ValueError("Filing identity changed during resolution")
            return ready
        raise KeyError(f"Unknown dev filing: {selected_id}")

    def prepare(self, filing: VerifiedFiling, manifest_sha256: str, config: dict) -> PreparedFiling:
        ready = self._load(filing, config)
        if ready is not None:
            return ready
        directory = self._directory(filing, config)
        directory.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".building-", dir=directory.parent) as temporary:
            workspace = Path(temporary)
            index = build_index(filing, workspace)
            if embedding_model_digest(EMBEDDING_MODEL) != config["embedding_model"]["digest"]:
                raise RuntimeError(f"Embedding model changed during indexing: {filing.ticker} {filing.year}")
            metadata = {
                "schema_version": 1, "filing_id": filing_id(filing), "ticker": filing.ticker,
                "filing_year": filing.year, "accession": filing.accession, "sec_url": filing.sec_url,
                "source_sha256": filing.sha256, "manifest_sha256": manifest_sha256,
                "index_version": directory.name, "index_configuration": config,
                "index_sha256": index["sha256"], "chunk_count": index["chunk_count"],
            }
            (workspace / METADATA_FILENAME).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            for name in ("output_parser.txt", "output_cleaner.txt", "all_embeddings.json"):
                (workspace / name).unlink(missing_ok=True)
            if hash_file(workspace / INDEX_FILENAME) != index["sha256"]:
                raise ValueError(f"Index changed before publication: {filing.ticker} {filing.year}")
            try:
                os.rename(workspace, directory)
            except OSError as error:
                if error.errno not in (errno.EEXIST, errno.ENOTEMPTY) or not directory.exists():
                    raise
        ready = self._load(filing, config)
        if ready is None:
            raise RuntimeError(f"Index disappeared during publication: {filing.ticker} {filing.year}")
        return ready

    def prepare_dev(self) -> list[PreparedFiling]:
        digest, filings = self.dev_filings()
        config = _configuration()
        return [self.prepare(filing, digest, config) for filing in filings.values()]

    def prepare_selected(self, ticker: str, year: int) -> PreparedFiling:
        digest, filing = self.verified(ticker, year)
        return self.prepare(filing, digest, _configuration())


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare manifest-verified dev filing indexes.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--index-root", type=Path)
    args = parser.parse_args()
    try:
        for filing in FilingIndexStore(args.manifest, args.index_root).prepare_dev():
            print(f"{filing.ticker} {filing.year}: {filing.filing_id} ({filing.chunk_count} chunks)")
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
