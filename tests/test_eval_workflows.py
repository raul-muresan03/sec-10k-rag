import json

import pytest

import etl_pipeline
from eval import run_eval
from tests.eval_helpers import make_question, write_manifest, write_questions


@pytest.mark.parametrize("split", ["dev", "test"])
@pytest.mark.parametrize("mode,top_n", [("full", 5), ("retrieval-only", 10)])
def test_modes_isolate_synthetic_splits_and_keep_saved_artifacts_consistent(
    tmp_path, monkeypatch, split, mode, top_n,
):
    questions = [
        make_question("dev-narrative", evidence=["dev evidence"]),
        make_question("dev-multi", "multi_hop", ["first", "second"]),
        make_question("dev-no-answer", "no_answer", [], None),
        make_question("test-numeric", "numeric", ["test evidence"], "10", "AAPL", 2024, "test"),
        make_question("test-no-answer", "no_answer", [], None, "AAPL", 2024, "test"),
    ]
    questions_path = tmp_path / "questions.jsonl"
    write_questions(questions_path, questions)
    manifest_path = write_manifest(tmp_path, questions)
    indexed = []
    retrieval_calls = []
    generation_calls = []

    def build_index(filing, directory):
        indexed.append((filing.ticker, filing.year, filing.split))
        assert etl_pipeline.DATA_DIR != directory
        assert directory.is_dir()
        return {"sha256": "test-index", "chunk_count": 10}

    def retrieve(question, k, index_path):
        retrieval_calls.append((question, k, index_path))
        assert index_path.parent.is_dir()
        text = "dev evidence first second" if "dev" in question else "test evidence"
        return [(0.9, text)]

    def generate(question, chunks, model):
        generation_calls.append(question)
        return ("Information not found in the provided context." if "no-answer" in question else "10", {})

    monkeypatch.setattr(run_eval, "build_index", build_index)
    monkeypatch.setattr(run_eval, "get_most_similar_chunks", retrieve)
    monkeypatch.setattr(run_eval, "get_llm_response", generate)
    summary, results_path, summary_path = run_eval.run_evaluation(
        split=split, limit=None, top_n=top_n, model="synthetic-model", mode=mode,
        questions_path=questions_path, manifest_path=manifest_path,
        output_directory=tmp_path / "runs",
    )

    selected = [q for q in questions if q["split"] == split]
    records = [json.loads(line) for line in results_path.read_text().splitlines()]
    assert json.loads(summary_path.read_text()) == summary
    assert {record["id"] for record in records} == {question["id"] for question in selected}
    assert all(record["run_id"] == summary["run_id"] for record in records)
    assert summary["split"] == split and summary["mode"] == mode
    assert summary["metrics"]["questions"] == len(selected)
    assert summary["metrics"]["filings"] == len(indexed) == 1
    assert summary["provenance"]["filings"][0]["ticker"] == selected[0]["ticker"]
    assert indexed == [(selected[0]["ticker"], selected[0]["year"], split)]
    assert len(retrieval_calls) == len(selected)
    assert all(k == top_n for _, k, _ in retrieval_calls)

    if mode == "retrieval-only":
        assert generation_calls == []
        assert all("generated_answer" not in record for record in records)
        assert "abstention" not in summary["metrics"]
        assert summary["metrics"]["retrieval"]["hit_at_10"]["questions"] == len(selected) - 1
    else:
        assert len(generation_calls) == len(selected)
        assert all("generated_answer" in record for record in records)
        assert summary["metrics"]["abstention"]["no_answer_correct"] == {
            "abstained": 1, "questions": 1, "rate": 1.0,
        }


@pytest.mark.parametrize("mode,top_n", [("full", 5), ("retrieval-only", 10)])
def test_missing_manifest_metadata_stops_before_index_or_generation(tmp_path, monkeypatch, mode, top_n):
    questions = [make_question("q1")]
    questions_path = tmp_path / "questions.jsonl"
    write_questions(questions_path, questions)
    manifest_path = write_manifest(tmp_path, questions)
    manifest = json.loads(manifest_path.read_text())
    del manifest["filings"][0]["accession"]
    manifest_path.write_text(json.dumps(manifest))

    monkeypatch.setattr(run_eval, "build_index", lambda *args: pytest.fail("indexed invalid manifest"))
    monkeypatch.setattr(run_eval, "get_most_similar_chunks", lambda *args: pytest.fail("retrieved invalid manifest"))
    monkeypatch.setattr(run_eval, "get_llm_response", lambda *args: pytest.fail("generated invalid manifest"))
    with pytest.raises(ValueError, match="Missing manifest field: accession"):
        run_eval.run_evaluation(
            "dev", None, top_n, "synthetic-model", questions_path,
            tmp_path / "runs", manifest_path, mode,
        )
    assert not (tmp_path / "runs").exists()


def test_full_run_records_false_refusal_separately_from_valid_no_answer(tmp_path, monkeypatch):
    questions = [
        make_question("valid-no-answer", "no_answer", [], None),
        make_question("answerable", evidence=["Gold passage"]),
    ]
    questions_path = tmp_path / "questions.jsonl"
    write_questions(questions_path, questions)
    manifest_path = write_manifest(tmp_path, questions)
    monkeypatch.setattr(run_eval, "build_index", lambda *args: {"sha256": "test-index"})
    monkeypatch.setattr(run_eval, "get_most_similar_chunks", lambda *args: [(0.9, "Gold passage")])
    monkeypatch.setattr(
        run_eval, "get_llm_response",
        lambda *args: ("Information not found in the provided context.", {}),
    )

    summary, results_path, _ = run_eval.run_evaluation(
        "dev", None, 5, "synthetic-model", questions_path,
        tmp_path / "runs", manifest_path,
    )
    rows = [json.loads(line) for line in results_path.read_text().splitlines()]
    assert [row["abstained"] for row in rows] == [True, True]
    assert summary["metrics"]["retrieval"]["hit_at_5"]["hits"] == 1
    assert summary["metrics"]["abstention"]["no_answer_correct"]["abstained"] == 1
    assert summary["metrics"]["abstention"]["answerable_false_abstentions"]["abstained"] == 1
    assert summary["provenance"]["answer_review_status"] == "not_applied"
