"""Dev-only evaluation of a frozen runtime snapshot, without rebuilding indexes."""

from datetime import datetime, timezone
import json
from math import isfinite
from pathlib import Path
import time

import etl_pipeline
from etl_pipeline.filings import catalog_filings, hash_file
from etl_pipeline.model_config import ModelConfig
from etl_pipeline.runtime_snapshot import SnapshotStore
from etl_pipeline.snapshot_query import query_snapshot
from eval.answer_reviews import RUBRIC_VERSION
from eval.retrieval_metrics import evidence_found, score_retrieval, summarize_retrieval
from eval.runtime_metrics import runtime_environment, summarize_stage_timings


def run_snapshot_evaluation(split: str, limit: int | None, top_n: int, config: ModelConfig,
                            questions_path: Path, output_directory: Path | None, manifest_path: Path,
                            mode: str, store: SnapshotStore | None = None,
                            question_interval_seconds: float = 0.0) -> tuple[dict, Path, Path]:
    from eval.run_eval import is_abstention, load_questions, summarize_results

    if split != "dev":
        raise ValueError("Public cloud snapshots support only dev evaluation; test is reserved for final evaluation")
    if top_n > 10:
        raise ValueError("Cloud top-n must be at most 10")
    if not isfinite(question_interval_seconds) or not 0 <= question_interval_seconds <= 120:
        raise ValueError("Cloud evaluation question interval must be between 0 and 120 seconds")
    snapshot = store if store is not None else SnapshotStore.from_env()
    manifest_hash = hash_file(manifest_path)
    if manifest_hash != snapshot.manifest["corpus_manifest_sha256"]:
        raise ValueError("Cloud evaluation corpus does not match the frozen snapshot")
    catalog = catalog_filings(manifest_path)
    questions_hash = hash_file(questions_path)
    questions = load_questions(questions_path, split, limit)
    if questions_hash != hash_file(questions_path) or manifest_hash != hash_file(manifest_path):
        raise ValueError("Cloud evaluation inputs changed while loading")
    selected = {}
    for question in questions:
        filing = snapshot.resolve(question["ticker"], question["year"])
        if filing.filing_id not in catalog or catalog[filing.filing_id].sha256 != filing.source_sha256:
            raise ValueError("Cloud evaluation filing provenance mismatch")
        selected[filing.filing_id] = filing
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-dev-cloud"
    results, scored = [], []
    next_question = time.monotonic()
    for question in questions:
        time.sleep(max(0.0, next_question - time.monotonic()))
        next_question = time.monotonic() + question_interval_seconds
        filing = snapshot.resolve(question["ticker"], question["year"])
        outcome = query_snapshot(snapshot, filing.filing_id, question["question"], top_n, config,
                                 generate=mode == "full")
        result = {
            "run_id": run_id, "id": question["id"], "split": "dev", "ticker": filing.ticker, "year": filing.year,
            "question_type": question["type"], "question": question["question"], "reference_answer": question["answer"],
            "section": question.get("section"), "expected_evidence": question["evidence"],
            "retrieved_chunks": [{"score": score, "text": text} for score, text in outcome.chunks],
            "latency_seconds": {"retrieval": outcome.retrieval_seconds, "total": outcome.total_seconds},
        }
        if mode == "retrieval-only":
            score = score_retrieval(question, outcome.chunks)
            scored.append((question, score))
            result.update(retrieval_score=score, evidence_found=[rank is not None for rank in score["evidence_ranks"]])
        else:
            result.update(generated_answer=outcome.answer, provider_metrics=outcome.metrics,
                          evidence_found=[evidence_found(passage, outcome.chunks) for passage in question["evidence"]],
                          abstained=is_abstention(outcome.answer or ""))
            result["latency_seconds"]["generation"] = outcome.generation_seconds
        results.append(result)
    loading_times = [0.0] * len(selected)
    if mode == "retrieval-only":
        metrics = {"questions": len(results), "filings": len(selected), "retrieval": summarize_retrieval(scored),
                   "latency_seconds": summarize_stage_timings(loading_times, results, include_generation=False)}
    else:
        metrics = summarize_results(results, loading_times, top_n)
        metrics.pop("ollama_reported", None)
        metrics["provider_usage"] = _provider_usage(results)
    payload = {
        "run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(), "mode": mode, "split": "dev",
        "model": config.model if mode == "full" else None, "top_n": top_n, "limit": limit,
        "runtime_environment": runtime_environment(),
        "provenance": {
            "snapshot_id": snapshot.snapshot_id, "embedding_config_id": snapshot.embedding_config_id,
            "questions": {"sha256": questions_hash, "path": str(questions_path.resolve())},
            "corpus_manifest": {"version": 1, "sha256": manifest_hash, "path": str(manifest_path.resolve())},
            "filings": [entry for entry in snapshot.manifest["filings"] if entry["filing_id"] in selected],
            "index_configuration": snapshot.manifest["index_configuration"],
            "generation_model": {
                "provider": "groq", "tag": config.model, "revision": None,
                "prompt_source_sha256": hash_file(Path(etl_pipeline.__file__).parent / "rag_engine.py"),
            } if mode == "full" else None,
            "retrieval": {"strategy": "dense_cosine", "top_n": top_n,
                          "relevance_proxy": "casefold_whitespace_substring"},
            "query_timeout_seconds": config.query_timeout_seconds, "rubric_version": RUBRIC_VERSION,
            "question_interval_seconds": question_interval_seconds,
            "answer_review_status": "not_applied",
            "model_identity_note": "Provider model IDs are mutable; the checksummed snapshot freezes document vectors.",
            "indexing_note": "Frozen indexes were read, not rebuilt. Cold loading is measured separately.",
        },
        "metrics": metrics,
    }
    output = output_directory if output_directory is not None else etl_pipeline.DATA_DIR / "eval-runs"
    output.mkdir(parents=True, exist_ok=True)
    results_path, summary_path = output / f"{run_id}.jsonl", output / f"{run_id}.summary.json"
    results_path.write_text("".join(json.dumps(result, ensure_ascii=False) + "\n" for result in results), encoding="utf-8")
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload, results_path, summary_path


def _provider_usage(results: list[dict]) -> dict[str, int]:
    totals = {key: 0 for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    for result in results:
        usage = result["provider_metrics"].get("usage")
        if isinstance(usage, dict):
            for key in totals:
                value = usage.get(key)
                if type(value) is int and value >= 0:
                    totals[key] += value
    return totals
