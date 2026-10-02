"""Cloud run metadata and a separate command for writing completed evaluation artifacts."""

from datetime import datetime, timezone
import json
from pathlib import Path

import etl_pipeline
from etl_pipeline.filings import hash_file
from etl_pipeline.model_config import ModelConfig
from etl_pipeline.runtime_snapshot import SnapshotStore
from eval.answer_reviews import RUBRIC_VERSION
from eval.runtime_metrics import runtime_environment


def snapshot_run_payload(run_id: str, config: ModelConfig, snapshot: SnapshotStore, mode: str,
                         top_n: int, limit: int | None, interval: float, inputs: dict, metrics: dict) -> dict:
    return {
        "run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(), "mode": mode, "split": "dev",
        "model": config.model if mode == "full" else None, "top_n": top_n, "limit": limit,
        "runtime_environment": runtime_environment(),
        "provenance": {
            **inputs, "snapshot_id": snapshot.snapshot_id, "embedding_config_id": snapshot.embedding_config_id,
            "index_configuration": snapshot.manifest["index_configuration"],
            "generation_model": {
                "provider": "groq", "tag": config.model, "revision": None,
                "prompt_source_sha256": hash_file(Path(etl_pipeline.__file__).parent / "rag_engine.py"),
            } if mode == "full" else None,
            "retrieval": {"strategy": "dense_cosine", "top_n": top_n,
                          "relevance_proxy": "casefold_whitespace_substring"},
            "query_timeout_seconds": config.query_timeout_seconds, "rubric_version": RUBRIC_VERSION,
            "question_interval_seconds": interval, "answer_review_status": "not_applied",
            "model_identity_note": (
                "Provider model IDs are mutable; the checksummed snapshot freezes document vectors."
            ),
            "indexing_note": "Frozen indexes were read, not rebuilt. Cold loading is measured separately.",
        },
        "metrics": metrics,
    }


def write_evaluation_artifacts(payload: dict, results: list[dict], results_path: Path, summary_path: Path) -> None:
    results_path.parent.mkdir(parents=True, exist_ok=True)
    records = "".join(json.dumps(result, ensure_ascii=False) + "\n" for result in results)
    results_path.write_text(records, encoding="utf-8")
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
