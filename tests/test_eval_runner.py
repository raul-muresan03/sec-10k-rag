import json
from collections import Counter

import pytest

from eval import run_eval


def make_question(
    question_id="q1",
    question_type="narrative",
    evidence=None,
    answer="expected",
    ticker="NVDA",
    year=2026,
    split="dev",
):
    return {
        "id": question_id,
        "split": split,
        "ticker": ticker,
        "year": year,
        "type": question_type,
        "question": f"Question {question_id}?",
        "answer": answer,
        "section": "Item 1" if answer is not None else None,
        "evidence": evidence if evidence is not None else ["Expected evidence"],
    }


def write_questions(path, questions):
    path.write_text("".join(json.dumps(question) + "\n" for question in questions))


def test_load_questions_filters_split_and_limit(tmp_path):
    questions_path = tmp_path / "questions.jsonl"
    questions = [
        make_question("dev-1"),
        make_question("test-1", split="test"),
        make_question("dev-2", ticker="AMZN", year=2021),
    ]
    write_questions(questions_path, questions)

    selected = run_eval.load_questions(questions_path, split="dev", limit=1)

    assert [question["id"] for question in selected] == ["dev-1"]


def test_load_questions_rejects_invalid_records(tmp_path):
    questions_path = tmp_path / "questions.jsonl"
    questions_path.write_text('{"id":"q1"}\n')

    with pytest.raises(ValueError, match="line 1"):
        run_eval.load_questions(questions_path, split="dev", limit=None)


def test_evidence_matches_case_insensitive_whitespace_normalized_chunks():
    chunks = [(0.9, "Header\n  EXPECTED   evidence text\nFooter")]

    assert run_eval.evidence_found("Expected evidence text", chunks)
    assert not run_eval.evidence_found("Different passage", chunks)


def test_summarize_results_separates_retrieval_and_abstention():
    records = [
        {
            "question_type": "multi_hop",
            "reference_answer": "expected",
            "evidence_found": [True, False],
            "abstained": False,
            "latency_seconds": {"retrieval": 0.2, "generation": 1.0},
        },
        {
            "question_type": "no_answer",
            "reference_answer": None,
            "evidence_found": [],
            "abstained": True,
            "latency_seconds": {"retrieval": 0.4, "generation": 1.2},
        },
        {
            "question_type": "narrative",
            "reference_answer": "expected",
            "evidence_found": [False],
            "abstained": True,
            "latency_seconds": {"retrieval": 0.6, "generation": 0.8},
        },
    ]

    summary = run_eval.summarize_results(records, indexing_seconds=[2.0], top_n=5)

    assert summary["retrieval"]["hit_at_5"] == {"hits": 1, "questions": 2, "rate": 0.5}
    assert summary["retrieval"]["multi_hop_all_evidence_at_5"] == {
        "complete": 0,
        "questions": 1,
        "rate": 0.0,
    }
    assert summary["abstention"]["no_answer_correct"] == {
        "abstained": 1,
        "questions": 1,
        "rate": 1.0,
    }
    assert summary["abstention"]["answerable_false_abstentions"] == {
        "abstained": 1,
        "questions": 2,
        "rate": 0.5,
    }
    assert summary["latency_seconds"]["indexing_mean"] == 2.0
    assert summary["latency_seconds"]["retrieval_mean"] == pytest.approx(0.4)


def test_run_evaluation_indexes_once_per_filing_and_saves_results(tmp_path, monkeypatch):
    questions_path = tmp_path / "questions.jsonl"
    output_directory = tmp_path / "results"
    questions = [
        make_question("nvda-1", evidence=["First evidence"]),
        make_question("nvda-2", evidence=["Second evidence"]),
        make_question("amzn-1", ticker="AMZN", year=2021, evidence=["Other evidence"]),
    ]
    write_questions(questions_path, questions)
    indexed = []
    retrieved = []

    def ensure_index(ticker, year):
        indexed.append((ticker, year))

    def get_chunks(question, top_n):
        retrieved.append((question, top_n))
        evidence = question.replace("Question ", "").rstrip("?")
        return [(0.9, f"Expected evidence for {evidence}")]

    monkeypatch.setattr(run_eval, "ensure_index", ensure_index)
    monkeypatch.setattr(run_eval, "get_most_similar_chunks", get_chunks)
    monkeypatch.setattr(
        run_eval,
        "get_llm_response",
        lambda question, chunks, model: ("Generated answer", {"eval_count": 3}),
    )

    summary, results_path, summary_path = run_eval.run_evaluation(
        split="dev",
        limit=None,
        top_n=5,
        model="test-model",
        questions_path=questions_path,
        output_directory=output_directory,
    )

    assert Counter(indexed) == Counter({("NVDA", 2026): 1, ("AMZN", 2021): 1})
    assert len(retrieved) == 3
    assert summary["metrics"]["questions"] == 3
    assert results_path.is_file()
    assert summary_path.is_file()
    saved = [json.loads(line) for line in results_path.read_text().splitlines()]
    assert len(saved) == 3
    assert saved[0]["generated_answer"] == "Generated answer"
    assert saved[0]["retrieved_chunks"] == [
        {"score": 0.9, "text": "Expected evidence for nvda-1"}
    ]
