"""Build a deterministic, provenance-bound snapshot for the static demo."""

import json
from pathlib import Path
from typing import Any

from eval.answer_reviews import summarize_reviews
from eval.provenance import hash_file

from demo.public import validate_snapshot
from demo.sources import load_sources, read_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTION = ROOT / "demo" / "selection.v1.json"
DEFAULT_OUTPUT = ROOT / "frontend" / "public" / "demo.v1.json"


def source_paths(root: Path, selection: dict) -> dict[str, Path]:
    answer = root / "data" / "eval-runs" / f"{selection['answer_run']['id']}.jsonl"
    retrieval = root / "data" / "eval-runs" / f"{selection['retrieval_run']['id']}.jsonl"
    return {
        "questions": root / "eval" / "questions.jsonl",
        "manifest": root / "eval" / "corpus_manifest.v1.json",
        "reviews": root / "eval" / "reviews" / "dev_baseline.v1.json",
        "answer": answer, "answer_summary": answer.with_suffix(".summary.json"),
        "retrieval": retrieval, "retrieval_summary": retrieval.with_suffix(".summary.json"),
    }


def validate_selection(selection: dict, gold: dict) -> list[str]:
    if selection.get("schema_version") != 1:
        raise ValueError("Unsupported demo selection version")
    ids = selection.get("examples")
    if not isinstance(ids, list) or not ids or any(not isinstance(item, str) for item in ids):
        raise ValueError("Select at least one dev question ID")
    if len(set(ids)) != len(ids) or any(item not in gold for item in ids):
        raise ValueError("Selection contains duplicate, unknown or held-out test question IDs")
    return ids


def make_example(question_id: str, sources: dict, answer_run_id: str, filings: dict) -> dict:
    question = sources["gold"][question_id]
    answer = sources["answers"][question_id]
    review = sources["reviews"][question_id]
    filing = filings[(question["ticker"], question["year"])]
    chunks = answer["retrieved_chunks"]
    if len(chunks) != 5 or any(not isinstance(c.get("text"), str) or not c["text"] for c in chunks):
        raise ValueError(f"Invalid saved answer context for {question_id}")
    if not isinstance(answer.get("generated_answer"), str):
        raise ValueError(f"Missing generated answer for {question_id}")
    if (len(answer["evidence_found"]) != len(question["evidence"])
            or any(type(value) is not bool for value in answer["evidence_found"])):
        raise ValueError(f"Invalid answer-run evidence flags for {question_id}")
    return {
        "id": question_id, "answer_run_id": answer_run_id,
        "ticker": question["ticker"], "filing_year": question["year"],
        "question_type": question["type"], "question": question["question"],
        "generated_answer": answer["generated_answer"], "reference_answer": question["answer"],
        "reference_evidence": question["evidence"], "section": question.get("section"),
        "reference_verification_note": question.get("verification_note"),
        "answer_run_evidence_found": answer["evidence_found"],
        "review": {field: review[field] for field in ("status", "confidence", "verdict", "dimensions", "explanation")},
        "sec_url": filing["sec_url"], "accession": filing["accession"],
        "retrieved_context": [
            {"rank": rank, "score": chunk["score"], "text": chunk["text"]}
            for rank, chunk in enumerate(chunks, 1)
        ],
    }


def build_snapshot(root: Path = ROOT, selection_path: Path = DEFAULT_SELECTION) -> dict[str, Any]:
    selection = read_json(selection_path)
    paths = source_paths(root, selection)
    sources = load_sources(selection, paths)
    chosen = validate_selection(selection, sources["gold"])
    gold = sources["gold"]
    answer_run_id, retrieval_run_id = selection["answer_run"]["id"], selection["retrieval_run"]["id"]
    answer_summary, retrieval_summary = sources["answer_summary"], sources["retrieval_summary"]
    provenance = retrieval_summary["provenance"]
    filings = {(f["ticker"], f["filing_year"]): f for f in sources["manifest"]["filings"]
               if f["split"] == "dev"}
    review_summary = summarize_reviews(sources["answers"], sources["reviews"])
    review_payload = read_json(paths["reviews"])
    snapshot = {
        "schema_version": 1,
        "dataset": {"split": "dev", "questions": len(gold),
                    "answerable": sum(q["type"] != "no_answer" for q in gold.values()),
                    "no_answer": sum(q["type"] == "no_answer" for q in gold.values()),
                    "filings": len(filings)},
        "runs": {
            "answers": {"run_id": answer_run_id, "jsonl_sha256": selection["answer_run"]["sha256"],
                        "split": "dev", "mode": "full", "top_n": answer_summary["top_n"],
                        "generation_model_tag": answer_summary["model"],
                        "provenance_note": "Legacy full run; immutable model and index identities were not saved."},
            "retrieval": {"run_id": retrieval_run_id, "jsonl_sha256": selection["retrieval_run"]["sha256"],
                          "split": "dev", "mode": "retrieval-only", "top_n": retrieval_summary["top_n"],
                          "embedding_model": provenance["index_configuration"]["embedding_model"],
                          "questions_sha256": provenance["questions"]["sha256"],
                          "manifest_sha256": provenance["corpus_manifest"]["sha256"],
                          "filings": [{"ticker": f["ticker"], "filing_year": f["filing_year"],
                                       "accession": f["accession"], "source_sha256": f["source_sha256"],
                                       "index_sha256": f["index"]["sha256"]}
                                      for f in provenance["filings"]]},
        },
        "retrieval_metrics": {"run_id": retrieval_run_id, "method": "strict quoted-evidence text matching",
                              "scope": "answerable dev questions; not answer correctness",
                              "values": sources["metrics"]},
        "answer_review": {"run_id": answer_run_id, "run_sha256": review_payload["run_sha256"],
                          "reviews_sha256": hash_file(paths["reviews"]),
                          "rubric_version": review_payload["rubric_version"],
                          "assessment_source": review_payload["assessment_source"],
                          "summary": review_summary},
        "examples": [make_example(question_id, sources, answer_run_id, filings) for question_id in chosen],
    }
    validate_snapshot(snapshot, root)
    return snapshot


def write_snapshot(snapshot: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
