import json
from hashlib import sha256
from pathlib import Path

import pytest

from eval.answer_reviews import (
    RUBRIC_VERSION, compare_runs, create_review_template, load_reviewed_run, summarize_reviews,
)


def write_run(tmp_path, name, questions):
    path = tmp_path / f"{name}.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in questions), encoding="utf-8")
    return path


def answer(question_id="q1", text="Response", gold="Gold"):
    return {
        "id": question_id,
        "split": "dev",
        "question": f"Question {question_id}?",
        "ticker": "NVDA",
        "year": 2026,
        "question_type": "narrative",
        "reference_answer": gold,
        "expected_evidence": ["quoted passage"],
        "retrieved_chunks": [{"score": 0.9, "text": "quoted passage"}],
        "generated_answer": text,
        "evidence_found": [True],
    }


def reviewed(question_id="q1", verdict="pass", status="ai_reviewed"):
    return {
        "question_id": question_id,
        "status": status,
        "confidence": "high",
        "verdict": verdict,
        "dimensions": {
            "completeness": "pass", "faithfulness": "pass", "numeric_precision": "not_applicable",
            "abstention": "pass", "citations": "not_applicable",
        },
        "explanation": "Supported by the first retrieved chunk.",
        "evidence_consulted": ["gold:questions.jsonl", "retrieved:R1"],
    }


def write_reviews(path, run, reviews):
    payload = {
        "rubric_version": "answer-review-v1", "run_id": run.stem,
        "run_sha256": sha256(run.read_bytes()).hexdigest(), "reviews": reviews,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_template_has_no_inferred_labels_and_summary_counts_only_reviewed(tmp_path):
    run = write_run(tmp_path, "baseline", [answer("q1"), answer("q2"), answer("q3")])
    template = create_review_template(run)
    assert template["run_id"] == "baseline"
    assert all(record["status"] == "unreviewed" and record["verdict"] is None for record in template["reviews"])

    template["reviews"][0] = reviewed("q1", "partial", "needs_owner_confirmation")
    template["reviews"][1] = reviewed("q2", "incorrect", "ai_reviewed")
    review_path = tmp_path / "reviews.json"
    review_path.write_text(json.dumps(template), encoding="utf-8")
    _, records, reviews = load_reviewed_run(run, review_path)
    summary = summarize_reviews(records, reviews)

    assert summary["questions"] == 3
    assert summary["reviewed"] == 2
    assert summary["unreviewed"] == 1
    assert summary["pending_owner_confirmation"] == 1
    assert summary["verdicts"] == {"pass": 0, "partial": 1, "incorrect": 1}
    assert summary["publication_status"] == "provisional"


def test_review_is_bound_to_exact_run_and_unknown_or_duplicate_ids_fail(tmp_path):
    run = write_run(tmp_path, "baseline", [answer()])
    reviews_path = tmp_path / "reviews.json"
    write_reviews(reviews_path, run, [reviewed()])

    changed = write_run(tmp_path, "candidate", [answer(text="Different answer")])
    with pytest.raises(ValueError, match="run ID mismatch"):
        load_reviewed_run(changed, reviews_path)

    run.write_text(run.read_text().replace("Response", "Different answer"), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_reviewed_run(run, reviews_path)
    run = write_run(tmp_path, "baseline", [answer()])

    write_reviews(reviews_path, run, [reviewed("missing")])
    with pytest.raises(ValueError, match="Unknown question"):
        load_reviewed_run(run, reviews_path)
    write_reviews(reviews_path, run, [reviewed(), reviewed()])
    with pytest.raises(ValueError, match="Duplicate review"):
        load_reviewed_run(run, reviews_path)


def test_review_rejects_invalid_status_and_dimension_values(tmp_path):
    run = write_run(tmp_path, "baseline", [answer()])
    review_path = tmp_path / "reviews.json"
    invalid = reviewed()
    invalid["dimensions"]["citations"] = "pass"
    write_reviews(review_path, run, [invalid])
    with pytest.raises(ValueError, match="citations"):
        load_reviewed_run(run, review_path)

    invalid = reviewed(status="unreviewed")
    write_reviews(review_path, run, [invalid])
    with pytest.raises(ValueError, match="Unreviewed"):
        load_reviewed_run(run, review_path)


def test_comparison_uses_only_same_gold_and_both_reviewed(tmp_path):
    baseline = write_run(tmp_path, "baseline", [answer("q1", "Old"), answer("q2", "Old")])
    candidate = write_run(tmp_path, "candidate", [answer("q1", "New"), answer("q2", "New")])
    baseline_reviews = tmp_path / "baseline.review.json"
    candidate_reviews = tmp_path / "candidate.review.json"
    write_reviews(baseline_reviews, baseline, [reviewed("q1", "incorrect"), reviewed("q2")])
    write_reviews(candidate_reviews, candidate, [reviewed("q1", "pass")])

    comparison = compare_runs(baseline, baseline_reviews, candidate, candidate_reviews)
    assert comparison["comparable_questions"] == 1
    assert comparison["transitions"] == {"incorrect -> pass": 1}
    assert comparison["baseline"] == {"reviewed": 2, "unreviewed": 0}
    assert comparison["candidate"] == {"reviewed": 1, "unreviewed": 1}

    candidate = write_run(tmp_path, "candidate", [answer("q1", "New", gold="Changed"), answer("q2")])
    write_reviews(candidate_reviews, candidate, [reviewed("q1", "pass")])
    with pytest.raises(ValueError, match="gold/question mismatch"):
        compare_runs(baseline, baseline_reviews, candidate, candidate_reviews)


def test_retrieval_only_run_cannot_be_answer_reviewed(tmp_path):
    run = write_run(tmp_path, "retrieval", [{"id": "q1", "retrieved_chunks": []}])
    with pytest.raises(ValueError, match="generated_answer"):
        create_review_template(run)


def test_tracked_baseline_has_every_dev_question_and_records_owner_confirmation():
    root = Path(__file__).resolve().parent.parent
    payload = json.loads((root / "eval/reviews/dev_baseline.v1.json").read_text(encoding="utf-8"))
    gold = [json.loads(line) for line in (root / "eval/questions.jsonl").read_text(encoding="utf-8").splitlines()]
    dev_ids = {question["id"] for question in gold if question["split"] == "dev"}
    reviews = payload["reviews"]

    assert payload["rubric_version"] == RUBRIC_VERSION
    assert len(reviews) == len(dev_ids) == 24
    assert {review["question_id"] for review in reviews} == dev_ids
    assert sum(review["verdict"] == "pass" for review in reviews) == 11
    assert sum(review["verdict"] == "partial" for review in reviews) == 6
    assert sum(review["verdict"] == "incorrect" for review in reviews) == 7
    assert {review["question_id"] for review in reviews if review["status"] == "owner_confirmed"} == {
        "adbe-2018-narrative", "adbe-2018-multi-hop", "pfe-2015-narrative", "pfe-2015-multi-hop",
    }
    assert not any(review["status"] == "needs_owner_confirmation" for review in reviews)
