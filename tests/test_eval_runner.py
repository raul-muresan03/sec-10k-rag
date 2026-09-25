import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from eval import run_eval
from eval import provenance
import etl_pipeline
from tests.eval_helpers import make_question, write_manifest, write_questions


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


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("Information not available in the provided context.", True),
        ("  INFORMATION NOT FOUND in the provided context!  ", True),
        ("Information not found in the provided context. Revenue was $10 billion.", False),
        ("The filing says information is not available in the provided context.", False),
        ("Revenue was $10 billion.", False),
    ],
)
def test_is_abstention_only_accepts_supported_full_responses(answer, expected):
    assert run_eval.is_abstention(answer) is expected


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
    manifest_path = write_manifest(tmp_path, questions)
    indexed = []
    retrieved = []

    def build_index(filing, directory):
        indexed.append((filing.ticker, filing.year))
        assert etl_pipeline.DATA_DIR == directory
        return {"strategy": "test", "sha256": "abc", "chunk_count": 1}

    def get_chunks(question, top_n):
        retrieved.append((question, top_n))
        evidence = question.replace("Question ", "").rstrip("?")
        return [(0.9, f"Expected evidence for {evidence}")]

    monkeypatch.setattr(run_eval, "build_index", build_index)
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
        manifest_path=manifest_path,
    )

    assert Counter(indexed) == Counter({("NVDA", 2026): 1, ("AMZN", 2021): 1})
    assert len(retrieved) == 3
    assert summary["metrics"]["questions"] == 3
    assert summary["provenance"]["questions"]["sha256"] == sha256(questions_path.read_bytes()).hexdigest()
    assert summary["provenance"]["corpus_manifest"]["sha256"] == sha256(manifest_path.read_bytes()).hexdigest()
    assert summary["provenance"]["index_configuration"]["embedding_model"]["tag"] == "nomic-embed-text"
    assert summary["provenance"]["generation_model"]["tag"] == "test-model"
    assert summary["provenance"]["generation_model"]["digest"] is None
    assert len(summary["provenance"]["generation_model"]["prompt_source_sha256"]) == 64
    assert summary["provenance"]["retrieval"]["top_n"] == 5
    assert summary["runtime_environment"]["platform"]
    assert summary["runtime_environment"]["python"]
    assert len(summary["provenance"]["filings"]) == 2
    assert all(f["index"]["sha256"] == "abc" for f in summary["provenance"]["filings"])
    assert all(f["indexing_seconds"] >= 0 for f in summary["provenance"]["filings"])
    assert {path.name for path in output_directory.iterdir()} == {results_path.name, summary_path.name}
    assert results_path.is_file()
    assert summary_path.is_file()
    saved = [json.loads(line) for line in results_path.read_text().splitlines()]
    assert len(saved) == 3
    assert saved[0]["generated_answer"] == "Generated answer"
    assert saved[0]["run_id"] == summary["run_id"]
    assert summary["metrics"]["latency_seconds"]["indexing"]["total"] == pytest.approx(
        sum(f["indexing_seconds"] for f in summary["provenance"]["filings"])
    )
    assert summary["metrics"]["ollama_reported"]["eval_count"]["total"] == 9
    assert summary["metrics"]["ollama_reported"]["prompt_eval_count"]["total"] is None
    assert "cost_usd" not in summary["metrics"]
    assert saved[0]["retrieved_chunks"] == [
        {"score": 0.9, "text": "Expected evidence for nvda-1"}
    ]


def test_run_evaluation_scores_alternate_abstention_in_saved_results(tmp_path, monkeypatch):
    questions_path = tmp_path / "questions.jsonl"
    write_questions(
        questions_path,
        [make_question("pfe-2015-no-answer", "no_answer", [], None, "PFE", 2015)],
    )
    manifest_path = write_manifest(tmp_path, [make_question("pfe-2015-no-answer", "no_answer", [], None, "PFE", 2015)])
    monkeypatch.setattr(run_eval, "build_index", lambda filing, directory: {"sha256": "abc"})
    monkeypatch.setattr(run_eval, "get_most_similar_chunks", lambda question, top_n: [])
    monkeypatch.setattr(
        run_eval,
        "get_llm_response",
        lambda question, chunks, model: ("Information not found in the provided context.", {}),
    )

    summary, results_path, _ = run_eval.run_evaluation(
        split="dev",
        limit=None,
        top_n=5,
        model="test-model",
        questions_path=questions_path,
        output_directory=tmp_path / "results",
        manifest_path=manifest_path,
    )

    result = json.loads(results_path.read_text().splitlines()[0])
    assert result["abstained"] is True
    assert summary["metrics"]["abstention"]["no_answer_correct"]["abstained"] == 1


def test_verify_filings_rejects_tampered_source_and_header(tmp_path):
    question = make_question()
    manifest_path = write_manifest(tmp_path, [question])
    key = ("NVDA", 2026)
    version, digest, selected = provenance.verify_filings(manifest_path, {key}, "dev")
    assert version == 1
    assert digest == sha256(manifest_path.read_bytes()).hexdigest()
    assert selected[key].accession == "0000000000-26-000001"

    source = selected[key].path
    source.write_text(source.read_text() + "tampered")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        provenance.verify_filings(manifest_path, {key}, "dev")

    source.write_text(source.read_text().replace("ACCESSION NUMBER: 0000000000-26-000001", "ACCESSION NUMBER: wrong"))
    manifest = json.loads(manifest_path.read_text())
    manifest["filings"][0]["sha256"] = sha256(source.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="header accession"):
        provenance.verify_filings(manifest_path, {key}, "dev")


def test_verify_filings_rejects_wrong_manifest_accession_or_split(tmp_path):
    manifest_path = write_manifest(tmp_path, [make_question()])
    manifest = json.loads(manifest_path.read_text())
    manifest["filings"][0]["accession"] = "other"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="accession/path/hash"):
        provenance.verify_filings(manifest_path, {("NVDA", 2026)}, "dev")
    manifest["filings"][0]["accession"] = "0000000000-26-000001"
    manifest["filings"][0]["split"] = "test"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Split mismatch"):
        provenance.verify_filings(manifest_path, {("NVDA", 2026)}, "dev")


def test_preflight_rejects_missing_second_filing_before_indexing(tmp_path, monkeypatch):
    questions = [make_question(), make_question("q2", ticker="AMZN", year=2021)]
    path = tmp_path / "questions.jsonl"
    write_questions(path, questions)
    manifest_path = write_manifest(tmp_path, questions)
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest["filings"]:
        if entry["ticker"] == "AMZN":
            (tmp_path / entry["path"]).unlink()
    monkeypatch.setattr(run_eval, "build_index", lambda *args: pytest.fail("indexing before preflight"))
    with pytest.raises(ValueError, match="Filing missing"):
        run_eval.run_evaluation("dev", None, 5, "test-model", path, tmp_path / "results", manifest_path)
    assert not (tmp_path / "results").exists()


def test_build_index_ignores_existing_active_index(tmp_path, monkeypatch):
    manifest_path = write_manifest(tmp_path, [make_question()])
    filing = provenance.verify_filings(manifest_path, {("NVDA", 2026)}, "dev")[2][("NVDA", 2026)]
    active_dir = tmp_path / "active"
    active_dir.mkdir()
    (active_dir / "active_accession.txt").write_text(filing.accession)
    (active_dir / "all_chunks_embeddings.json").write_text('old index')
    monkeypatch.setattr(etl_pipeline, "DATA_DIR", active_dir)
    calls = []

    def parse(path):
        calls.append(path)
        (etl_pipeline.DATA_DIR / "output_parser.txt").write_text("parsed")

    def clean(path):
        (etl_pipeline.DATA_DIR / "output_cleaner.txt").write_text("cleaned")

    def chunk(path):
        (etl_pipeline.DATA_DIR / "all_chunks_embeddings.json").write_text(
            json.dumps({"chunks": ["fresh"], "embeddings": [[0.1]]})
        )

    monkeypatch.setattr(provenance, "parse_10K", parse)
    monkeypatch.setattr(provenance, "clean_10K", clean)
    monkeypatch.setattr(provenance, "chunk_10K", chunk)
    with TemporaryDirectory(dir=tmp_path) as temporary:
        directory = Path(temporary)
        with provenance.use_index_directory(directory):
            metadata = provenance.build_index(filing, directory)
    assert calls == [str(filing.path)]
    assert metadata["chunk_count"] == 1
    assert metadata["sha256"] == sha256(b'{"chunks": ["fresh"], "embeddings": [[0.1]]}').hexdigest()
    assert etl_pipeline.DATA_DIR == active_dir
    assert (active_dir / "all_chunks_embeddings.json").read_text() == "old index"


def test_failed_index_restores_active_directory_and_removes_workspace(tmp_path, monkeypatch):
    questions_path = tmp_path / "questions.jsonl"
    questions = [make_question()]
    write_questions(questions_path, questions)
    manifest_path = write_manifest(tmp_path, questions)
    active_dir = etl_pipeline.DATA_DIR

    def fail_index(filing, directory):
        assert etl_pipeline.DATA_DIR == directory
        raise RuntimeError("index failed")

    monkeypatch.setattr(run_eval, "build_index", fail_index)
    with pytest.raises(RuntimeError, match="index failed"):
        run_eval.run_evaluation("dev", None, 5, "model", questions_path, tmp_path / "results", manifest_path)
    assert etl_pipeline.DATA_DIR == active_dir
    assert not list((tmp_path / "results").iterdir())


def test_retrieval_only_retrieves_once_at_ten_without_generation(tmp_path, monkeypatch):
    questions = [
        make_question("q1", "multi_hop", ["first", "second"]),
        make_question("q2", "no_answer", [], None),
    ]
    questions_path = tmp_path / "questions.jsonl"
    write_questions(questions_path, questions)
    manifest_path = write_manifest(tmp_path, questions)
    indexed = []
    retrieved = []

    def build_index(filing, directory):
        indexed.append((filing.ticker, filing.year))
        return {"sha256": "fake-index"}

    def get_chunks(question, top_n):
        retrieved.append((question, top_n))
        if question == "Question q1?":
            return [(1.0, "not relevant")] * 5 + [(0.5, "first and second")]
        return [(1.0, "context without gold evidence")]

    monkeypatch.setattr(run_eval, "build_index", build_index)
    monkeypatch.setattr(run_eval, "get_most_similar_chunks", get_chunks)
    monkeypatch.setattr(
        run_eval, "get_llm_response", lambda *args: pytest.fail("retrieval-only invoked generation")
    )
    summary, records_path, summary_path = run_eval.run_evaluation(
        split="dev", limit=None, top_n=10, model="ignored", mode="retrieval-only",
        questions_path=questions_path, output_directory=tmp_path / "results", manifest_path=manifest_path,
    )

    assert indexed == [("NVDA", 2026)]
    assert retrieved == [("Question q1?", 10), ("Question q2?", 10)]
    assert summary_path.is_file()
    assert summary["mode"] == "retrieval-only"
    assert summary["model"] is None
    assert summary["provenance"]["generation_model"] is None
    assert summary["metrics"]["retrieval"]["hit_at_5"]["hits"] == 0
    assert summary["metrics"]["retrieval"]["hit_at_10"] == {"hits": 1, "questions": 1, "rate": 1.0}
    assert summary["metrics"]["retrieval"]["mrr_at_10"]["rate"] == pytest.approx(1 / 6)
    assert summary["metrics"]["retrieval"]["multi_hop_all_evidence_at_10"]["complete"] == 1
    assert "abstention" not in summary["metrics"]
    assert "ollama_reported" not in summary["metrics"]
    assert "generation" not in summary["metrics"]["latency_seconds"]
    assert summary["metrics"]["latency_seconds"]["retrieval"]["count"] == 2
    records = [json.loads(line) for line in records_path.read_text().splitlines()]
    assert [row["id"] for row in records] == ["q1", "q2"]
    assert records[0]["retrieval_score"]["evidence_ranks"] == [6, 6]
    assert records[0]["evidence_found"] == [True, True]
    assert records[1]["retrieval_score"]["reciprocal_rank_at_10"] is None
    assert all("generated_answer" not in row and "ollama" not in row for row in records)


def test_retrieval_only_requires_top_ten(tmp_path):
    with pytest.raises(ValueError, match="exactly 10"):
        run_eval.run_evaluation("dev", None, 5, "unused", mode="retrieval-only")
