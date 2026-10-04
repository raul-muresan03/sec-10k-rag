"""Dev-only queries and scoring against a frozen snapshot; no artifact writes."""

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
import time

from etl_pipeline.filings import catalog_filings, hash_file
from etl_pipeline.model_config import ModelConfig
from etl_pipeline.runtime_snapshot import SnapshotStore
from etl_pipeline.snapshot_query import query_snapshot
from eval.cloud_provenance import snapshot_run_payload
from eval.retrieval_metrics import evidence_found, score_retrieval, summarize_retrieval
from eval.runtime_metrics import summarize_stage_timings


@dataclass(frozen=True)
class EvaluationInputs:
    questions: list[dict]
    snapshot: SnapshotStore
    selected_ids: set[str]
    questions_path: Path
    questions_sha256: str
    manifest_path: Path
    manifest_sha256: str


def _load_inputs(questions_path: Path, manifest_path: Path, snapshot: SnapshotStore,
                 split: str, limit: int | None) -> EvaluationInputs:
    from eval.run_eval import load_questions

    manifest_hash = hash_file(manifest_path)
    if manifest_hash != snapshot.manifest["corpus_manifest_sha256"]:
        raise ValueError("Cloud evaluation corpus does not match the frozen snapshot")
    catalog = catalog_filings(manifest_path, split)
    questions_hash = hash_file(questions_path)
    questions = load_questions(questions_path, split, limit)
    if questions_hash != hash_file(questions_path) or manifest_hash != hash_file(manifest_path):
        raise ValueError("Cloud evaluation inputs changed while loading")
    selected = set()
    for question in questions:
        filing = snapshot.resolve(question["ticker"], question["year"])
        if filing.filing_id not in catalog or catalog[filing.filing_id].sha256 != filing.source_sha256:
            raise ValueError("Cloud evaluation filing provenance mismatch")
        selected.add(filing.filing_id)
    return EvaluationInputs(
        questions, snapshot, selected, questions_path, questions_hash, manifest_path, manifest_hash,
    )


def _question_result(question: dict, snapshot: SnapshotStore, top_n: int, config: ModelConfig,
                      mode: str, run_id: str) -> tuple[dict, dict | None]:
    from eval.run_eval import is_abstention

    filing = snapshot.resolve(question["ticker"], question["year"])
    outcome = query_snapshot(snapshot, filing.filing_id, question["question"], top_n, config, generate=mode == "full")
    result = {
        "run_id": run_id, "id": question["id"], "split": question["split"], "ticker": filing.ticker,
        "year": filing.year,
        "question_type": question["type"], "question": question["question"],
        "reference_answer": question["answer"], "section": question.get("section"),
        "expected_evidence": question["evidence"],
        "retrieved_chunks": [{"score": score, "text": text} for score, text in outcome.chunks],
        "latency_seconds": {"retrieval": outcome.retrieval_seconds, "total": outcome.total_seconds},
    }
    if mode == "retrieval-only":
        score = score_retrieval(question, outcome.chunks)
        result.update(retrieval_score=score, evidence_found=[rank is not None for rank in score["evidence_ranks"]])
        return result, score
    result.update(generated_answer=outcome.answer, provider_metrics=outcome.metrics,
                  evidence_found=[evidence_found(passage, outcome.chunks) for passage in question["evidence"]],
                  abstained=is_abstention(outcome.answer or ""))
    result["latency_seconds"]["generation"] = outcome.generation_seconds
    return result, None


def _question_results(inputs: EvaluationInputs, config: ModelConfig, top_n: int, mode: str,
                       run_id: str, interval: float) -> tuple[list[dict], list[tuple[dict, dict]]]:
    results, scored = [], []
    next_question = time.monotonic()
    for question in inputs.questions:
        time.sleep(max(0.0, next_question - time.monotonic()))
        next_question = time.monotonic() + interval
        result, score = _question_result(question, inputs.snapshot, top_n, config, mode, run_id)
        if score is not None:
            scored.append((question, score))
        results.append(result)
    return results, scored


def _metrics(results: list[dict], scored: list[tuple[dict, dict]], filing_count: int,
             mode: str, top_n: int) -> dict:
    from eval.run_eval import summarize_results

    if mode == "retrieval-only":
        return {
            "questions": len(results), "filings": filing_count, "retrieval": summarize_retrieval(scored),
            "latency_seconds": summarize_stage_timings([], results, include_generation=False),
        }
    metrics = summarize_results(results, [], top_n)
    metrics["filings"] = filing_count
    metrics.pop("ollama_reported", None)
    metrics["provider_usage"] = _provider_usage(results)
    return metrics


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


def evaluate_snapshot(split: str, limit: int | None, top_n: int, config: ModelConfig, questions_path: Path,
                       manifest_path: Path, mode: str, store: SnapshotStore | None = None,
                       question_interval_seconds: float = 0.0, final: bool = False) -> tuple[dict, list[dict]]:
    if split == "test" and (not final or store is None):
        raise ValueError("Test questions are reserved for final evaluation with explicit frozen indexes")
    if split not in ("dev", "test"):
        raise ValueError(f"split must be dev or test, got {split}")
    if top_n > 10:
        raise ValueError("Cloud top-n must be at most 10")
    if not isfinite(question_interval_seconds) or not 0 <= question_interval_seconds <= 120:
        raise ValueError("Cloud evaluation question interval must be between 0 and 120 seconds")
    snapshot = store if store is not None else SnapshotStore.from_env()
    inputs = _load_inputs(questions_path, manifest_path, snapshot, split, limit)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + f"-{split}-cloud"
    results, scored = _question_results(inputs, config, top_n, mode, run_id, question_interval_seconds)
    metrics = _metrics(results, scored, len(inputs.selected_ids), mode, top_n)
    provenance = {
        "questions": {"sha256": inputs.questions_sha256, "path": str(questions_path.resolve())},
        "corpus_manifest": {"version": 1, "sha256": inputs.manifest_sha256, "path": str(manifest_path.resolve())},
        "filings": [entry for entry in snapshot.manifest["filings"] if entry["filing_id"] in inputs.selected_ids],
    }
    payload = snapshot_run_payload(run_id, config, snapshot, mode, top_n, limit, question_interval_seconds,
                                   provenance, metrics, split)
    return payload, results
