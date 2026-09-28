import json

import pytest

from demo.export import ROOT, build_snapshot, write_snapshot
from demo.public import validate_snapshot
from eval.answer_reviews import create_review_template
from eval.provenance import hash_file
from eval.retrieval_metrics import score_retrieval, summarize_retrieval
from tests.eval_helpers import make_question, write_manifest, write_questions


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def replay(tmp_path):
    questions = [
        make_question("dev-numeric", "numeric", ["Revenue in 2020 was $10 billion"], "$10 billion"),
        make_question("dev-no-answer", "no_answer", [], None),
        make_question("held-out-secret", "numeric", ["Secret evidence"], "Secret answer", "AAPL", 2024, "test"),
    ]
    gold = tmp_path / "eval" / "questions.jsonl"
    gold.parent.mkdir(parents=True)
    write_questions(gold, questions)
    manifest_path = write_manifest(tmp_path, questions)
    manifest = json.loads(manifest_path.read_text())
    for filing in manifest["filings"]:
        filing["sec_url"] = "https://www.sec.gov/Archives/example/" + filing["accession"] + ".txt"
    save_json(manifest_path, manifest)

    run_dir = tmp_path / "data" / "eval-runs"
    run_dir.mkdir(parents=True)
    answer_id, retrieval_id = "synthetic-dev", "synthetic-dev-retrieval"
    answer_path = run_dir / f"{answer_id}.jsonl"
    retrieval_path = run_dir / f"{retrieval_id}.jsonl"
    answer_rows, retrieval_rows, scored = [], [], []
    for question in questions[:2]:
        fields = {"id": question["id"], "split": question["split"], "ticker": question["ticker"],
                  "year": question["year"], "question_type": question["type"],
                  "question": question["question"], "reference_answer": question["answer"],
                  "section": question["section"], "expected_evidence": question["evidence"]}
        text = "Revenue in 2020 was $10 billion | 2020 | (in billions)" if question["answer"] else "Not relevant"
        five = [{"score": 0.9, "text": text}] * 5
        ten = five + [{"score": 0.5, "text": "irrelevant"}] * 5
        answer_rows.append({**fields, "run_id": answer_id, "generated_answer": "Answer" if question["answer"]
                            else "Information not found in the provided context.",
                            "evidence_found": [True] if question["answer"] else [], "retrieved_chunks": five})
        score = score_retrieval(question, [(c["score"], c["text"]) for c in ten])
        retrieval_rows.append({**fields, "run_id": retrieval_id, "retrieved_chunks": ten,
                               "retrieval_score": score,
                               "evidence_found": [rank is not None for rank in score["evidence_ranks"]]})
        scored.append((question, score))
    for path, rows in ((answer_path, answer_rows), (retrieval_path, retrieval_rows)):
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    reviews = create_review_template(answer_path)
    reviews["assessment_source"] = "synthetic fixture"
    save_json(tmp_path / "eval" / "reviews" / "dev_baseline.v1.json", reviews)
    save_json(answer_path.with_suffix(".summary.json"), {
        "split": "dev", "top_n": 5, "limit": None, "model": "synthetic-model",
        "metrics": {"questions": 2, "filings": 1},
    })
    dev_filing = next(f for f in manifest["filings"] if f["split"] == "dev")
    save_json(retrieval_path.with_suffix(".summary.json"), {
        "run_id": retrieval_id, "split": "dev", "top_n": 10, "limit": None, "mode": "retrieval-only",
        "model": None, "metrics": {"questions": 2, "filings": 1, "retrieval": summarize_retrieval(scored)},
        "provenance": {
            "questions": {"sha256": hash_file(gold)},
            "corpus_manifest": {"sha256": hash_file(manifest_path), "version": 1},
            "index_configuration": {"embedding_model": {"tag": "synthetic", "digest": None}},
            "filings": [{"ticker": dev_filing["ticker"], "filing_year": dev_filing["filing_year"],
                         "accession": dev_filing["accession"], "source_sha256": dev_filing["sha256"],
                         "index": {"sha256": "synthetic-index"}}],
        },
    })
    selection_path = tmp_path / "demo" / "selection.v1.json"
    save_json(selection_path, {
        "schema_version": 1, "answer_run": {"id": answer_id, "sha256": hash_file(answer_path)},
        "retrieval_run": {"id": retrieval_id, "sha256": hash_file(retrieval_path)},
        "examples": ["dev-numeric", "dev-no-answer"],
    })
    return tmp_path, selection_path, answer_path, retrieval_path


def test_synthetic_export_is_dev_only_and_valid_without_saved_runs(replay):
    root, selection_path, answer_path, retrieval_path = replay
    snapshot = build_snapshot(root, selection_path)
    assert [e["id"] for e in snapshot["examples"]] == ["dev-numeric", "dev-no-answer"]
    assert snapshot["retrieval_metrics"]["values"]["hit_at_10"]["hits"] == 1
    assert snapshot["examples"][0]["retrieved_context"][0]["text"].endswith("(in billions)")
    output = root / "demo" / "snapshot.v1.json"
    write_snapshot(snapshot, output)
    assert "held-out-secret" not in output.read_text()
    answer_path.unlink()
    retrieval_path.unlink()
    validate_snapshot(json.loads(output.read_text()), root)


def test_rejects_tampered_run_hash(replay):
    root, selection, answer, _ = replay
    answer.write_text(answer.read_text() + "\n")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        build_snapshot(root, selection)


def test_rejects_mismatched_gold_ids(replay):
    root, selection, _, _ = replay
    gold_path = root / "eval" / "questions.jsonl"
    gold_path.write_text(gold_path.read_text().replace('"dev-numeric"', '"changed-id"'))
    with pytest.raises(ValueError, match="question IDs"):
        build_snapshot(root, selection)


def test_rejects_test_selection_and_test_example_in_committed_snapshot(replay):
    root, selection_path, _, _ = replay
    selection = json.loads(selection_path.read_text())
    selection["examples"].append("held-out-secret")
    save_json(selection_path, selection)
    with pytest.raises(ValueError, match="held-out test"):
        build_snapshot(root, selection_path)
    selection["examples"] = ["dev-numeric"]
    save_json(selection_path, selection)
    snapshot = build_snapshot(root, selection_path)
    snapshot["examples"][0]["id"] = "held-out-secret"
    with pytest.raises(ValueError, match="Non-dev"):
        validate_snapshot(snapshot, root)


def test_rejects_inconsistent_retrieval_summary_and_public_schema(replay):
    root, selection, _, retrieval = replay
    snapshot = build_snapshot(root, selection)
    snapshot["retrieval_metrics"]["values"]["hit_at_10"]["questions"] = 3
    with pytest.raises(ValueError, match="denominator/rate"):
        validate_snapshot(snapshot, root)
    summary_path = retrieval.with_suffix(".summary.json")
    summary = json.loads(summary_path.read_text())
    summary["metrics"]["retrieval"]["hit_at_10"]["hits"] = 0
    save_json(summary_path, summary)
    with pytest.raises(ValueError, match="summary differs"):
        build_snapshot(root, selection)


def test_committed_snapshot_validates_with_only_tracked_inputs():
    snapshot = json.loads((ROOT / "demo" / "snapshot.v1.json").read_text(encoding="utf-8"))
    validate_snapshot(snapshot)
    assert len(snapshot["examples"]) == 8
    assert snapshot["answer_review"]["summary"]["publication_status"] == "provisional"


def test_public_check_detects_outdated_review_and_selection(replay):
    root, selection_path, _, _ = replay
    snapshot = build_snapshot(root, selection_path)
    review_path = root / "eval" / "reviews" / "dev_baseline.v1.json"
    review_path.write_text(review_path.read_text() + "\n")
    with pytest.raises(ValueError, match="Public review differs"):
        validate_snapshot(snapshot, root)
    snapshot["answer_review"]["reviews_sha256"] = hash_file(review_path)
    selection = json.loads(selection_path.read_text())
    selection["examples"] = ["dev-no-answer", "dev-numeric"]
    save_json(selection_path, selection)
    with pytest.raises(ValueError, match="tracked selection"):
        validate_snapshot(snapshot, root)


def test_public_check_rejects_local_paths_and_extra_fields(replay):
    root, selection, _, _ = replay
    snapshot = build_snapshot(root, selection)
    snapshot["runs"]["retrieval"]["filings"][0]["source_path"] = "/home/user/private/data/file.txt"
    with pytest.raises(ValueError, match="public filing fields"):
        validate_snapshot(snapshot, root)
