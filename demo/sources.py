"""Validate saved evaluation artifacts before any public release."""

import json
from pathlib import Path

from eval.answer_reviews import load_reviewed_run
from eval.provenance import hash_file
from eval.retrieval_metrics import evidence_found, score_retrieval, summarize_retrieval
from eval.run_eval import load_questions


def read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def load_records(path: Path, expected_hash: str) -> dict[str, dict]:
    if hash_file(path) != expected_hash:
        raise ValueError(f"Run SHA-256 mismatch: {path}")
    records = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        question_id = record["id"]
        if question_id in records:
            raise ValueError(f"Duplicate question ID: {question_id}")
        records[question_id] = record
    if not records or hash_file(path) != expected_hash:
        raise ValueError(f"Empty or changed run: {path}")
    return records


def check_summary(summary: dict, run_id: str, split: str, top_n: int, question_count: int) -> None:
    if (summary.get("run_id", run_id) != run_id or summary.get("split") != split
            or summary.get("top_n") != top_n or summary.get("limit") is not None):
        raise ValueError(f"Unexpected run configuration: {run_id}")
    if summary["metrics"]["questions"] != question_count:
        raise ValueError(f"Run summary question count mismatch: {run_id}")


def check_gold(records: dict, gold: dict, run_id: str) -> None:
    if records.keys() != gold.keys():
        raise ValueError(f"Run question IDs do not match dev gold: {run_id}")
    mapping = {"split": "split", "ticker": "ticker", "year": "year", "question_type": "type",
               "question": "question", "reference_answer": "answer", "expected_evidence": "evidence"}
    for question_id, record in records.items():
        if record.get("run_id", run_id) != run_id:
            raise ValueError(f"Run ID mismatch for {question_id}")
        if any(record.get(field) != gold[question_id][source] for field, source in mapping.items()):
            raise ValueError(f"Gold question mismatch for {question_id}")
        if record.get("section") != gold[question_id].get("section"):
            raise ValueError(f"Gold section mismatch for {question_id}")


def check_provenance(summary: dict, manifest: dict, questions_path: Path, manifest_path: Path) -> None:
    provenance = summary["provenance"]
    if (provenance["questions"]["sha256"] != hash_file(questions_path)
            or provenance["corpus_manifest"]["sha256"] != hash_file(manifest_path)
            or provenance["corpus_manifest"]["version"] != manifest["version"]):
        raise ValueError("Retrieval provenance hash mismatch")
    filings = {(f["ticker"], f["filing_year"]): f for f in manifest["filings"] if f["split"] == "dev"}
    recorded = provenance["filings"]
    if (summary["metrics"]["filings"] != len(filings) or len(recorded) != len(filings)
            or len({(f["ticker"], f["filing_year"]) for f in recorded}) != len(filings)):
        raise ValueError("Retrieval provenance filing set mismatch")
    for filing in recorded:
        key = (filing["ticker"], filing["filing_year"])
        if key not in filings or any(
            filing[field] != filings[key][manifest_field]
            for field, manifest_field in (("accession", "accession"), ("source_sha256", "sha256"))
        ):
            raise ValueError("Retrieval filing differs from the dev manifest")


def check_retrieval(records: dict, gold: dict, summary: dict) -> dict:
    if summary.get("mode") != "retrieval-only" or summary.get("model") is not None:
        raise ValueError("Expected retrieval-only run")
    scored = []
    for question_id, record in records.items():
        chunks = record["retrieved_chunks"]
        if len(chunks) != 10 or any(not isinstance(c.get("text"), str) for c in chunks):
            raise ValueError(f"Invalid top-10 chunks for {question_id}")
        score = score_retrieval(gold[question_id], [(c["score"], c["text"]) for c in chunks])
        if record["retrieval_score"] != score or record["evidence_found"] != [
            rank is not None for rank in score["evidence_ranks"]
        ]:
            raise ValueError(f"Retrieval score mismatch for {question_id}")
        scored.append((gold[question_id], score))
    metrics = summarize_retrieval(scored)
    if metrics != summary["metrics"]["retrieval"]:
        raise ValueError("Retrieval summary differs from ranked records")
    return metrics


def check_answers(records: dict, gold: dict) -> None:
    for question_id, record in records.items():
        chunks = record["retrieved_chunks"]
        if (not isinstance(record.get("generated_answer"), str) or len(chunks) != 5
                or any(not isinstance(chunk.get("text"), str) for chunk in chunks)):
            raise ValueError(f"Invalid saved answer/context for {question_id}")
        found = [evidence_found(passage, [(c["score"], c["text"]) for c in chunks])
                 for passage in gold[question_id]["evidence"]]
        if record["evidence_found"] != found:
            raise ValueError(f"Answer-run evidence flags mismatch for {question_id}")


def load_sources(selection: dict, paths: dict[str, Path]) -> dict:
    gold = {q["id"]: q for q in load_questions(paths["questions"], "dev", None)}
    manifest = read_json(paths["manifest"])
    answer_id, retrieval_id = selection["answer_run"]["id"], selection["retrieval_run"]["id"]
    if paths["answer"].stem != answer_id or paths["retrieval"].stem != retrieval_id:
        raise ValueError("Selected run IDs do not match the artifacts")
    answers = load_records(paths["answer"], selection["answer_run"]["sha256"])
    retrieval = load_records(paths["retrieval"], selection["retrieval_run"]["sha256"])
    _, reviewed_records, reviews = load_reviewed_run(paths["answer"], paths["reviews"])
    if reviewed_records.keys() != answers.keys() or reviews.keys() != answers.keys():
        raise ValueError("Missing or mismatched answer reviews")
    answer_summary, retrieval_summary = read_json(paths["answer_summary"]), read_json(paths["retrieval_summary"])
    for records, summary, run_id, top_n in ((answers, answer_summary, answer_id, 5),
                                            (retrieval, retrieval_summary, retrieval_id, 10)):
        check_summary(summary, run_id, "dev", top_n, len(gold))
        check_gold(records, gold, run_id)
    if answer_summary["metrics"]["filings"] != len({(q["ticker"], q["year"]) for q in gold.values()}):
        raise ValueError("Answer filing count mismatch")
    check_answers(answers, gold)
    check_provenance(retrieval_summary, manifest, paths["questions"], paths["manifest"])
    metrics = check_retrieval(retrieval, gold, retrieval_summary)
    return dict(gold=gold, manifest=manifest, answers=answers, reviews=reviews,
                answer_summary=answer_summary, retrieval_summary=retrieval_summary, metrics=metrics)
