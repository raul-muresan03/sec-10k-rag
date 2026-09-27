"""Validate the committed public snapshot using only tracked repository files."""

from pathlib import Path

from eval.answer_reviews import summarize_reviews
from eval.provenance import hash_file
from eval.run_eval import load_questions

from demo.sources import read_json


ROOT = Path(__file__).resolve().parents[1]


def _check_fields(record: dict, expected: str, label: str) -> None:
    if set(record) != set(expected.split()):
        raise ValueError(f"Unexpected public {label} fields")


def _check_structure(snapshot: dict) -> None:
    _check_fields(snapshot, "schema_version dataset runs retrieval_metrics answer_review examples", "snapshot")
    _check_fields(snapshot["runs"], "answers retrieval", "runs")
    _check_fields(snapshot["runs"]["answers"],
                  "run_id jsonl_sha256 split mode top_n generation_model_tag provenance_note", "answer run")
    _check_fields(snapshot["runs"]["retrieval"],
                  "run_id jsonl_sha256 split mode top_n embedding_model questions_sha256 manifest_sha256 filings",
                  "retrieval run")
    _check_fields(snapshot["retrieval_metrics"], "run_id method scope values", "retrieval metrics")
    _check_fields(snapshot["answer_review"],
                  "run_id run_sha256 reviews_sha256 rubric_version assessment_source summary", "answer review")
    for filing in snapshot["runs"]["retrieval"]["filings"]:
        _check_fields(filing, "ticker filing_year accession source_sha256 index_sha256", "filing")
    for example in snapshot["examples"]:
        _check_fields(example, "id answer_run_id ticker filing_year question_type question generated_answer "
                      "reference_answer reference_evidence section reference_verification_note "
                      "answer_run_evidence_found review sec_url accession retrieved_context", "example")
        _check_fields(example["review"], "status confidence verdict dimensions explanation", "example review")
        for chunk in example["retrieved_context"]:
            _check_fields(chunk, "rank score text", "retrieved chunk")


def _check_rates(values: dict, answerable: int, multi_hop: int) -> None:
    def matches_rate(numerator: float, denominator: int, rate: float | None) -> bool:
        return rate == (numerator / denominator if denominator else None)

    for k in (5, 10):
        hits = values[f"hit_at_{k}"]
        complete = values[f"multi_hop_all_evidence_at_{k}"]
        if (hits["questions"] != answerable or not 0 <= hits["hits"] <= answerable
                or not matches_rate(hits["hits"], answerable, hits["rate"])
                or complete["questions"] != multi_hop or not 0 <= complete["complete"] <= multi_hop
                or not matches_rate(complete["complete"], multi_hop, complete["rate"])):
            raise ValueError("Public retrieval metric denominator/rate mismatch")
    mrr = values["mrr_at_10"]
    if (mrr["questions"] != answerable or not 0 <= mrr["reciprocal_rank_sum"] <= answerable
            or not matches_rate(mrr["reciprocal_rank_sum"], answerable, mrr["rate"])):
        raise ValueError("Public MRR denominator/rate mismatch")


def validate_snapshot(snapshot: dict, root: Path = ROOT) -> None:
    if snapshot.get("schema_version") != 1 or snapshot.get("dataset", {}).get("split") != "dev":
        raise ValueError("Invalid public snapshot version or split")
    _check_structure(snapshot)
    questions_path = root / "eval" / "questions.jsonl"
    manifest_path = root / "eval" / "corpus_manifest.v1.json"
    reviews_path = root / "eval" / "reviews" / "dev_baseline.v1.json"
    selection = read_json(root / "demo" / "selection.v1.json")
    gold = {q["id"]: q for q in load_questions(questions_path, "dev", None)}
    manifest = read_json(manifest_path)
    reviews_payload = read_json(reviews_path)
    reviews = {r["question_id"]: r for r in reviews_payload["reviews"]}
    filings = {(f["ticker"], f["filing_year"]): f for f in manifest["filings"] if f["split"] == "dev"}
    dataset = snapshot["dataset"]
    answerable = sum(q["type"] != "no_answer" for q in gold.values())
    multi_hop = sum(q["type"] == "multi_hop" for q in gold.values())
    if (dataset["questions"] != len(gold) or dataset["answerable"] != answerable
            or dataset["no_answer"] != len(gold) - answerable or dataset["filings"] != len(filings)):
        raise ValueError("Public dataset counts differ from dev gold")
    runs = snapshot["runs"]
    if (runs["answers"]["split"] != "dev" or runs["retrieval"]["split"] != "dev"
            or runs["answers"]["mode"] != "full" or runs["retrieval"]["mode"] != "retrieval-only"
            or runs["answers"]["top_n"] != 5 or runs["retrieval"]["top_n"] != 10
            or runs["retrieval"]["questions_sha256"] != hash_file(questions_path)
            or runs["retrieval"]["manifest_sha256"] != hash_file(manifest_path)
            or selection["schema_version"] != snapshot["schema_version"]
            or any(runs[key]["run_id"] != selection[source]["id"]
                   or runs[key]["jsonl_sha256"] != selection[source]["sha256"]
                   for key, source in (("answers", "answer_run"), ("retrieval", "retrieval_run")))):
        raise ValueError("Public run configuration/provenance mismatch")
    metric_payload, review_payload = snapshot["retrieval_metrics"], snapshot["answer_review"]
    if metric_payload["run_id"] != runs["retrieval"]["run_id"]:
        raise ValueError("Public retrieval run mismatch")
    _check_rates(metric_payload["values"], answerable, multi_hop)
    if (review_payload["run_id"] != runs["answers"]["run_id"]
            or review_payload["run_sha256"] != runs["answers"]["jsonl_sha256"]
            or review_payload["reviews_sha256"] != hash_file(reviews_path)
            or review_payload["rubric_version"] != reviews_payload["rubric_version"]
            or review_payload["assessment_source"] != reviews_payload["assessment_source"]
            or review_payload["summary"] != summarize_reviews(gold, reviews)):
        raise ValueError("Public review differs from the tracked review file")
    if not snapshot["examples"] or len({e["id"] for e in snapshot["examples"]}) != len(snapshot["examples"]):
        raise ValueError("Empty or duplicate public examples")
    for example in snapshot["examples"]:
        question_id = example["id"]
        if question_id not in gold:
            raise ValueError(f"Non-dev question in public snapshot: {question_id}")
        question = gold[question_id]
        filing = filings[(question["ticker"], question["year"])]
        if (example["answer_run_id"] != runs["answers"]["run_id"]
                or example["ticker"] != question["ticker"] or example["filing_year"] != question["year"]
                or example["question_type"] != question["type"] or example["question"] != question["question"]
                or example["reference_answer"] != question["answer"]
                or example["reference_evidence"] != question["evidence"]
                or example["reference_verification_note"] != question.get("verification_note")
                or example["section"] != question.get("section")
                or example["sec_url"] != filing["sec_url"] or example["accession"] != filing["accession"]
                or example["review"] != {key: reviews[question_id][key] for key in
                                          ("status", "confidence", "verdict", "dimensions", "explanation")}
                or len(example["retrieved_context"]) != 5
                or [chunk["rank"] for chunk in example["retrieved_context"]] != list(range(1, 6))):
            raise ValueError(f"Public example differs from dev gold/review: {question_id}")
    if [e["id"] for e in snapshot["examples"]] != selection["examples"]:
        raise ValueError("Public examples differ from the tracked selection")
    recorded = runs["retrieval"]["filings"]
    if len(recorded) != len(filings) or len({(f["ticker"], f["filing_year"]) for f in recorded}) != len(filings):
        raise ValueError("Public retrieval filing set mismatch")
    for filing in recorded:
        source = filings.get((filing["ticker"], filing["filing_year"]))
        if (source is None or filing["accession"] != source["accession"]
                or filing["source_sha256"] != source["sha256"]):
            raise ValueError("Public retrieval filing differs from the dev manifest")
