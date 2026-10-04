"""Final evaluation on the test split with frozen offline indexes; never touches the public export.

The four test filings are indexed with the frozen cloud configuration into the
operator cache only. No test export is published and the public bundle is unchanged.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

import etl_pipeline
from etl_pipeline.cloud_identity import configuration_id, embedding_configuration, index_configuration
from etl_pipeline.cloud_indexing import build_filing_indexes
from etl_pipeline.filings import MANIFEST_PATH, VerifiedFiling, filing_id
from etl_pipeline.model_config import ModelConfig
from etl_pipeline.snapshot_provenance import verify_index_metadata
from etl_pipeline.vector_store import load_index
from eval.cloud_eval import evaluate_snapshot
from eval.cloud_provenance import write_evaluation_artifacts
from eval.run_eval import QUESTIONS_PATH


FROZEN_BEHAVIOR_PATH = Path(__file__).with_name("frozen_behavior.v1.json")


def assert_frozen_behavior() -> dict:
    """Refuse test evaluation when indexing behavior drifted from the frozen contract."""
    import json

    contract = json.loads(FROZEN_BEHAVIOR_PATH.read_text(encoding="utf-8"))
    current = index_configuration()
    for section in ("embedding", "chunking"):
        if current[section] != contract["behavior"][section]:
            raise ValueError(f"Indexing {section} drifted from the frozen contract; refusing test evaluation")
    return contract


class FrozenTestIndexes:
    """Verified per-filing cloud indexes behind the snapshot query interface."""

    @dataclass(frozen=True)
    class Reference:
        filing_id: str
        ticker: str
        year: int
        source_sha256: str

    def __init__(self, manifest_path: Path, index_root: Path, config: ModelConfig,
                 selected: set[tuple[str, int]] | None) -> None:
        manifest_hash, identity, indexes = build_filing_indexes(
            manifest_path, index_root, config, selected=selected, split="test")
        self._manifest = {"corpus_manifest_sha256": manifest_hash, "index_configuration": identity,
                          "filings": []}
        self._filings: dict[str, VerifiedFiling] = {}
        self._indexes = {}
        versions = []
        for filing, path in indexes:
            verify_index_metadata(filing, path, identity)
            chunks, vectors = load_index(path)
            selected_id = filing_id(filing)
            self._filings[selected_id] = filing
            self._indexes[selected_id] = (tuple(chunks), tuple(tuple(vector) for vector in vectors))
            version = configuration_id({"source_sha256": filing.sha256,
                                        "configuration": identity})
            versions.append(version)
            self._manifest["filings"].append({
                "filing_id": selected_id, "ticker": filing.ticker, "filing_year": filing.year,
                "split": "test", "accession": filing.accession, "sec_url": filing.sec_url,
                "source_sha256": filing.sha256, "index_version": version, "chunk_count": len(chunks),
            })
        self.snapshot_id = configuration_id(sorted(versions))
        self.embedding_config_id = configuration_id(embedding_configuration())

    @property
    def manifest(self) -> dict:
        return {key: (list(value) if isinstance(value, list) else value)
                for key, value in self._manifest.items()}

    def catalog(self) -> dict[str, VerifiedFiling]:
        return dict(self._filings)

    def prepared(self) -> list[VerifiedFiling]:
        return list(self._filings.values())

    def resolve_id(self, selected_id: str) -> Reference:
        return self._reference(self._filings[selected_id])

    def resolve(self, ticker: str, year: int) -> Reference:
        for filing in self._filings.values():
            if (filing.ticker, filing.year) == (ticker.strip().upper(), year):
                return self._reference(filing)
        raise KeyError("Unknown frozen test filing")

    @classmethod
    def _reference(cls, filing: VerifiedFiling) -> Reference:
        return cls.Reference(filing_id=filing_id(filing), ticker=filing.ticker, year=filing.year,
                             source_sha256=filing.sha256)

    def index(self, selected_id: str) -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...]]:
        return self._indexes[selected_id]


def run_final_test_evaluation(top_n: int, config: ModelConfig, questions_path: Path,
                              manifest_path: Path, output_directory: Path | None,
                              index_root: Path, question_interval_seconds: float,
                              selected: set[tuple[str, int]] | None = None) -> tuple[dict, Path, Path]:
    if config.runtime != "cloud":
        raise ValueError("Final cloud evaluation requires the explicit cloud profile")
    contract = assert_frozen_behavior()
    store = FrozenTestIndexes(manifest_path, index_root, config, selected)
    if not store.prepared():
        raise ValueError("No frozen test filings selected")
    payload, records = evaluate_snapshot("test", None, top_n, config, questions_path, manifest_path,
                                         "full", store, question_interval_seconds, final=True)
    payload["provenance"]["frozen_behavior"] = {
        "contract": str(FROZEN_BEHAVIOR_PATH), "snapshot_id": contract["snapshot_id"],
        "index_config_id": contract["index_config_id"],
    }
    output = output_directory if output_directory is not None else etl_pipeline.DATA_DIR / "eval-runs"
    results_path = output / f"{payload['run_id']}.jsonl"
    summary_path = output / f"{payload['run_id']}.summary.json"
    write_evaluation_artifacts(payload, records, results_path, summary_path)
    return payload, results_path, summary_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Final test-split evaluation on frozen offline indexes.")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--index-root", type=Path, default=etl_pipeline.DATA_DIR / "cloud-indexes")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--question-interval-seconds", type=float, default=61.0)
    args = parser.parse_args()
    try:
        payload, results_path, summary_path = run_final_test_evaluation(
            args.top_n, ModelConfig.from_env(), QUESTIONS_PATH, MANIFEST_PATH, args.output,
            args.index_root, args.question_interval_seconds)
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))
    print(f"Run: {payload['run_id']}")
    print(f"Results: {results_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
