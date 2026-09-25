"""Human-review records bound to saved answer runs; never infer verdicts from retrieval hits."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


RUBRIC_VERSION = "answer-review-v1"
VERDICTS = ("pass", "partial", "incorrect")
STATUSES = ("unreviewed", "ai_reviewed", "needs_owner_confirmation", "owner_confirmed")
DIMENSIONS = ("completeness", "faithfulness", "numeric_precision", "abstention", "citations")
DIMENSION_VALUES = {"pass", "partial", "fail", "not_applicable", "not_assessed"}
GOLD_FIELDS = ("split", "question", "ticker", "year", "question_type", "reference_answer", "expected_evidence")


def _load_run(path: Path) -> tuple[dict[str, dict[str, Any]], str]:
    digest = sha256(path.read_bytes()).hexdigest()
    records = {}
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict) or not isinstance(record.get("id"), str) or not record["id"].strip():
                raise ValueError(f"Invalid answer record on line {line_number}: {path}")
            if "generated_answer" not in record or not isinstance(record["generated_answer"], str):
                raise ValueError(f"Answer record needs generated_answer on line {line_number}: {path}")
            if record["id"] in records or (record.get("run_id") is not None and record["run_id"] != path.stem):
                raise ValueError(f"Duplicate question ID or run ID mismatch on line {line_number}: {path}")
            for field in GOLD_FIELDS:
                if field not in record:
                    raise ValueError(f"Missing {field} in answer record on line {line_number}: {path}")
            records[record["id"]] = record
    if not records:
        raise ValueError(f"Empty answer run: {path}")
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError(f"Answer run changed while loading: {path}")
    return records, digest


def create_review_template(run_path: Path) -> dict[str, Any]:
    records, digest = _load_run(run_path)
    return {
        "rubric_version": RUBRIC_VERSION,
        "run_id": run_path.stem,
        "run_sha256": digest,
        "reviews": [
            {
                "question_id": question_id,
                "status": "unreviewed",
                "confidence": None,
                "verdict": None,
                "dimensions": {name: "not_applicable" if name == "citations" else "not_assessed"
                               for name in DIMENSIONS},
                "explanation": "",
                "evidence_consulted": [],
            }
            for question_id in records
        ],
    }


def _validate_review(review: dict[str, Any], question_id: str) -> None:
    if review.get("status") not in STATUSES:
        raise ValueError(f"Invalid review status for {question_id}")
    dimensions = review.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        raise ValueError(f"Invalid dimensions for {question_id}")
    if any(value not in DIMENSION_VALUES for value in dimensions.values()):
        raise ValueError(f"Invalid dimension value for {question_id}")
    if dimensions["citations"] != "not_applicable":
        raise ValueError(f"citations must be not_applicable for {question_id}")
    if review["status"] == "unreviewed":
        if review.get("verdict") is not None or review.get("confidence") is not None:
            raise ValueError(f"Unreviewed question cannot have a verdict or confidence: {question_id}")
        if any(value not in ("not_assessed", "not_applicable") for value in dimensions.values()):
            raise ValueError(f"Unreviewed question cannot have dimension scores: {question_id}")
        if review.get("explanation") != "" or review.get("evidence_consulted") != []:
            raise ValueError(f"Unreviewed question cannot have assessment notes: {question_id}")
        return
    if review.get("verdict") not in VERDICTS or review.get("confidence") not in ("high", "medium", "low"):
        raise ValueError(f"Invalid verdict or confidence for {question_id}")
    if not isinstance(review.get("explanation"), str) or not review["explanation"].strip():
        raise ValueError(f"Missing explanation for {question_id}")
    evidence = review.get("evidence_consulted")
    if (
        not isinstance(evidence, list) or not evidence
        or any(not isinstance(item, str) or not item for item in evidence)
    ):
        raise ValueError(f"Missing evidence_consulted for {question_id}")


def load_reviewed_run(
    run_path: Path, reviews_path: Path,
) -> tuple[str, dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    records, digest = _load_run(run_path)
    payload = json.loads(reviews_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("rubric_version") != RUBRIC_VERSION:
        raise ValueError(f"Review rubric version mismatch: {reviews_path}")
    if payload.get("run_id") != run_path.stem:
        raise ValueError(f"Review run ID mismatch: {reviews_path}")
    if payload.get("run_sha256") != digest:
        raise ValueError(f"Review run SHA-256 mismatch: {reviews_path}")
    if not isinstance(payload.get("reviews"), list):
        raise ValueError(f"Missing reviews list: {reviews_path}")
    reviews = {}
    for review in payload["reviews"]:
        if not isinstance(review, dict) or not isinstance(review.get("question_id"), str):
            raise ValueError(f"Invalid review in {reviews_path}")
        question_id = review["question_id"]
        if question_id not in records:
            raise ValueError(f"Unknown question in reviews: {question_id}")
        if question_id in reviews:
            raise ValueError(f"Duplicate review for {question_id}")
        _validate_review(review, question_id)
        reviews[question_id] = review
    return run_path.stem, records, reviews


def summarize_reviews(records: dict, reviews: dict) -> dict[str, Any]:
    reviewed = [review for review in reviews.values() if review["status"] != "unreviewed"]
    counts = Counter(review["verdict"] for review in reviewed)
    pending = sum(review["status"] == "needs_owner_confirmation" for review in reviewed)
    unreviewed = len(records) - len(reviewed)
    return {
        "questions": len(records),
        "reviewed": len(reviewed),
        "unreviewed": unreviewed,
        "pending_owner_confirmation": pending,
        "pending_owner_question_ids": sorted(
            question_id for question_id, review in reviews.items()
            if review["status"] == "needs_owner_confirmation"
        ),
        "unreviewed_question_ids": sorted(
            question_id for question_id in records
            if question_id not in reviews or reviews[question_id]["status"] == "unreviewed"
        ),
        "ai_reviewed": sum(review["status"] == "ai_reviewed" for review in reviewed),
        "owner_confirmed": sum(review["status"] == "owner_confirmed" for review in reviewed),
        "verdicts": {verdict: counts[verdict] for verdict in VERDICTS},
        "publication_status": "provisional" if pending or unreviewed else "owner_checkpoint_complete",
    }


def compare_runs(
    baseline_run: Path, baseline_reviews: Path, candidate_run: Path, candidate_reviews: Path,
) -> dict[str, Any]:
    baseline_id, baseline_records, first = load_reviewed_run(baseline_run, baseline_reviews)
    candidate_id, candidate_records, second = load_reviewed_run(candidate_run, candidate_reviews)
    shared_ids = baseline_records.keys() & candidate_records.keys()
    for question_id in shared_ids:
        if any(baseline_records[question_id][field] != candidate_records[question_id][field] for field in GOLD_FIELDS):
            raise ValueError(f"Run gold/question mismatch for {question_id}")
    comparable = sorted(
        question_id for question_id in shared_ids
        if question_id in first and question_id in second
        and first[question_id]["status"] != "unreviewed" and second[question_id]["status"] != "unreviewed"
    )
    transitions = Counter(f"{first[q]['verdict']} -> {second[q]['verdict']}" for q in comparable)
    baseline_summary = summarize_reviews(baseline_records, first)
    candidate_summary = summarize_reviews(candidate_records, second)
    return {
        "baseline_run_id": baseline_id, "candidate_run_id": candidate_id,
        "comparable_questions": len(comparable),
        "baseline": {key: baseline_summary[key] for key in ("reviewed", "unreviewed")},
        "candidate": {key: candidate_summary[key] for key in ("reviewed", "unreviewed")},
        "transitions": dict(sorted(transitions.items())),
    }
