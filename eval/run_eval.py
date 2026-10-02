import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from typing import Any

import etl_pipeline
from eval.answer_reviews import RUBRIC_VERSION
from eval.provenance import (
    MANIFEST_PATH, build_index, hash_file, index_configuration, verify_filings,
)
from eval.retrieval_metrics import evidence_found, normalize_text, score_retrieval, summarize_retrieval
from eval.runtime_metrics import runtime_environment, summarize_ollama, summarize_stage_timings
from etl_pipeline.rag_engine import get_llm_response
from etl_pipeline.model_config import ModelConfig
from etl_pipeline.vector_store import get_most_similar_chunks


DEFAULT_MODEL = "gemma3:1b"
DEFAULT_TOP_N = 5
RETRIEVAL_TOP_N = 10
MODES = {"full", "retrieval-only"}
ABSTENTION_TEXTS = {
    "information not available in the provided context",
    "information not found in the provided context",
}
QUESTION_TYPES = {"narrative", "numeric", "multi_hop", "no_answer"}
SPLITS = {"dev", "test"}
QUESTIONS_PATH = Path(__file__).with_name("questions.jsonl")


def is_abstention(answer: str) -> bool:
    return normalize_text(answer).rstrip(".! ") in ABSTENTION_TEXTS


def load_questions(
    path: Path,
    split: str,
    limit: int | None,
) -> list[dict[str, Any]]:
    if split not in SPLITS:
        raise ValueError(f"split must be one of: {', '.join(sorted(SPLITS))}")
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")

    questions = []
    identifiers = set()
    with path.open(encoding="utf-8") as questions_file:
        for line_number, line in enumerate(questions_file, start=1):
            if not line.strip():
                continue
            try:
                question = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {line_number}: {error}") from error
            _validate_question(question, line_number)
            if question["id"] in identifiers:
                raise ValueError(f"Duplicate question id on line {line_number}: {question['id']}")
            identifiers.add(question["id"])
            if question["split"] == split:
                questions.append(question)

    if limit is not None:
        questions = questions[:limit]
    if not questions:
        raise ValueError(f"No questions found for split '{split}'")
    return questions


def _validate_question(question: Any, line_number: int) -> None:
    required_fields = {
        "id",
        "split",
        "ticker",
        "year",
        "type",
        "question",
        "answer",
        "evidence",
    }
    if not isinstance(question, dict) or not required_fields.issubset(question):
        raise ValueError(f"Question on line {line_number} is missing required fields")
    if not isinstance(question["id"], str) or not question["id"].strip():
        raise ValueError(f"Question on line {line_number} has an invalid id")
    if question["split"] not in SPLITS:
        raise ValueError(f"Question on line {line_number} has an invalid split")
    if question["type"] not in QUESTION_TYPES:
        raise ValueError(f"Question on line {line_number} has an invalid type")
    if not isinstance(question["ticker"], str) or not question["ticker"].strip():
        raise ValueError(f"Question on line {line_number} has an invalid ticker")
    if not isinstance(question["year"], int) or isinstance(question["year"], bool):
        raise ValueError(f"Question on line {line_number} has an invalid year")
    if not isinstance(question["question"], str) or not question["question"].strip():
        raise ValueError(f"Question on line {line_number} has an invalid question")
    if not isinstance(question["evidence"], list) or any(
        not isinstance(passage, str) or not passage.strip()
        for passage in question["evidence"]
    ):
        raise ValueError(f"Question on line {line_number} has invalid evidence")

    if question["type"] == "no_answer":
        if question["answer"] is not None or question["evidence"]:
            raise ValueError(f"No-answer question on line {line_number} must have null answer and no evidence")
    elif not isinstance(question["answer"], str) or not question["answer"].strip():
        raise ValueError(f"Answerable question on line {line_number} must have an answer")
    elif question["type"] == "multi_hop" and len(question["evidence"]) < 2:
        raise ValueError(f"Multi-hop question on line {line_number} needs at least two evidence passages")
    elif not question["evidence"]:
        raise ValueError(f"Answerable question on line {line_number} needs evidence")


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def summarize_results(
    results: list[dict[str, Any]],
    indexing_seconds: list[float],
    top_n: int,
) -> dict[str, Any]:
    answerable = [result for result in results if result["reference_answer"] is not None]
    multi_hop = [result for result in answerable if result["question_type"] == "multi_hop"]
    no_answer = [result for result in results if result["question_type"] == "no_answer"]
    retrieval_hits = sum(any(result["evidence_found"]) for result in answerable)
    complete_multi_hop = sum(
        bool(result["evidence_found"]) and all(result["evidence_found"])
        for result in multi_hop
    )
    correct_abstentions = sum(result["abstained"] for result in no_answer)
    false_abstentions = sum(result["abstained"] for result in answerable)

    return {
        "questions": len(results),
        "filings": len(indexing_seconds),
        "retrieval": {
            f"hit_at_{top_n}": {
                "hits": retrieval_hits,
                "questions": len(answerable),
                "rate": _rate(retrieval_hits, len(answerable)),
            },
            f"multi_hop_all_evidence_at_{top_n}": {
                "complete": complete_multi_hop,
                "questions": len(multi_hop),
                "rate": _rate(complete_multi_hop, len(multi_hop)),
            },
        },
        "abstention": {
            "no_answer_correct": {
                "abstained": correct_abstentions,
                "questions": len(no_answer),
                "rate": _rate(correct_abstentions, len(no_answer)),
            },
            "answerable_false_abstentions": {
                "abstained": false_abstentions,
                "questions": len(answerable),
                "rate": _rate(false_abstentions, len(answerable)),
            },
        },
        "latency_seconds": summarize_stage_timings(indexing_seconds, results, include_generation=True),
        "ollama_reported": summarize_ollama(results),
    }


def run_evaluation(
    split: str,
    limit: int | None,
    top_n: int,
    model: str,
    questions_path: Path = QUESTIONS_PATH,
    output_directory: Path | None = None,
    manifest_path: Path = MANIFEST_PATH,
    mode: str = "full",
) -> tuple[dict[str, Any], Path, Path]:
    if mode not in MODES:
        raise ValueError(f"mode must be one of: {', '.join(sorted(MODES))}")
    if top_n < 1:
        raise ValueError("top-n must be greater than zero")
    if mode == "retrieval-only" and top_n != RETRIEVAL_TOP_N:
        raise ValueError("retrieval-only requires exactly 10 results (top-n=10)")
    ModelConfig.from_env(model=model).require_local_indexes()
    questions_hash = hash_file(questions_path)
    questions = load_questions(questions_path, split, limit)
    if questions_hash != hash_file(questions_path):
        raise ValueError(f"Questions file changed while loading: {questions_path}")
    grouped_questions: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for question in questions:
        key = (question["ticker"].strip().upper(), question["year"])
        grouped_questions.setdefault(key, []).append(question)

    manifest_version, manifest_hash, filings = verify_filings(manifest_path, set(grouped_questions), split)
    configuration = index_configuration()
    if output_directory is None:
        output_directory = etl_pipeline.DATA_DIR / "eval-runs"
    output_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_name = f"{timestamp}-{split}" if mode == "full" else f"{timestamp}-{split}-retrieval"
    results = []
    scored = []
    indexing_seconds = []
    filing_records = []
    for (ticker, year), filing_questions in grouped_questions.items():
        filing = filings[(ticker, year)]
        with TemporaryDirectory(prefix=f"{run_name}-{ticker}-", dir=output_directory) as temporary:
            index_dir = Path(temporary)
            indexing_start = time.perf_counter()
            index = build_index(filing, index_dir)
            indexing_duration = time.perf_counter() - indexing_start
            indexing_seconds.append(indexing_duration)
            filing_records.append({
                "ticker": ticker, "filing_year": year, "accession": filing.accession,
                "source_path": str(filing.path), "source_sha256": filing.sha256, "index": index,
                "indexing_seconds": indexing_duration,
            })

            for question in filing_questions:
                retrieval_start = time.perf_counter()
                chunks = get_most_similar_chunks(question["question"], top_n, index_dir / "all_chunks_embeddings.json")
                retrieval_seconds = time.perf_counter() - retrieval_start

                result = {
                    "run_id": run_name,
                    "id": question["id"],
                    "split": question["split"],
                    "ticker": ticker,
                    "year": year,
                    "question_type": question["type"],
                    "question": question["question"],
                    "reference_answer": question["answer"],
                    "section": question.get("section"),
                    "expected_evidence": question["evidence"],
                    "retrieved_chunks": [
                        {"score": score, "text": text} for score, text in chunks
                    ],
                    "latency_seconds": {"retrieval": retrieval_seconds},
                }
                if mode == "retrieval-only":
                    score = score_retrieval(question, chunks)
                    scored.append((question, score))
                    result["retrieval_score"] = score
                    result["evidence_found"] = [rank is not None for rank in score["evidence_ranks"]]
                    results.append(result)
                    continue

                generation_start = time.perf_counter()
                answer, ollama_metrics = get_llm_response(
                    question["question"], chunks, model
                )
                generation_seconds = time.perf_counter() - generation_start

                result.update({
                    "generated_answer": answer,
                    "evidence_found": [evidence_found(passage, chunks) for passage in question["evidence"]],
                    "abstained": is_abstention(answer),
                    "ollama": ollama_metrics,
                })
                result["latency_seconds"]["generation"] = generation_seconds
                results.append(result)

    if mode == "retrieval-only":
        summary = {
            "questions": len(results),
            "filings": len(indexing_seconds),
            "retrieval": summarize_retrieval(scored),
            "latency_seconds": summarize_stage_timings(indexing_seconds, results, include_generation=False),
        }
    else:
        summary = summarize_results(results, indexing_seconds, top_n)
    results_path = output_directory / f"{run_name}.jsonl"
    summary_path = output_directory / f"{run_name}.summary.json"

    with results_path.open("w", encoding="utf-8") as results_file:
        for result in results:
            results_file.write(json.dumps(result, ensure_ascii=False) + "\n")
    summary_payload = {
        "run_id": run_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "split": split,
        "model": model if mode == "full" else None,
        "top_n": top_n,
        "limit": limit,
        "runtime_environment": runtime_environment(),
        "provenance": {
            "questions": {"sha256": questions_hash, "path": str(questions_path.resolve())},
            "corpus_manifest": {
                "version": manifest_version, "sha256": manifest_hash,
                "path": str(manifest_path.resolve()),
            },
            "filings": filing_records,
            "index_configuration": configuration,
            "generation_model": (
                {
                    "tag": model, "digest": None,
                    "prompt_source_sha256": hash_file(Path(__file__).parent.parent / "etl_pipeline" / "rag_engine.py"),
                }
                if mode == "full" else None
            ),
            "retrieval": {
                "strategy": "dense_cosine", "top_n": top_n,
                "relevance_proxy": "casefold_whitespace_substring",
            },
            "rubric_version": RUBRIC_VERSION,
            "answer_review_status": "not_applied",
            "model_identity_note": "Ollama model tags are mutable; digests were not captured.",
        },
        "metrics": summary,
    }
    summary_path.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary_payload, results_path, summary_path


def _positive_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the SEC RAG pipeline.")
    parser.add_argument("--split", choices=sorted(SPLITS), default="dev")
    parser.add_argument("--mode", choices=sorted(MODES), default="full")
    parser.add_argument("--limit", type=_positive_integer)
    parser.add_argument("--top-n", type=_positive_integer)
    parser.add_argument("--model")
    parser.add_argument("--questions", type=Path, default=QUESTIONS_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()

    try:
        if args.mode == "retrieval-only" and args.top_n not in (None, RETRIEVAL_TOP_N):
            parser.error("retrieval-only requires top-n=10")
        if args.mode == "retrieval-only" and args.model is not None:
            parser.error("--model is only applicable in full mode")
        summary, results_path, summary_path = run_evaluation(
            split=args.split,
            limit=args.limit,
            top_n=RETRIEVAL_TOP_N if args.mode == "retrieval-only" else args.top_n or DEFAULT_TOP_N,
            model=ModelConfig.from_env(model=args.model).model,
            questions_path=args.questions,
            manifest_path=args.manifest,
            mode=args.mode,
        )
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))

    print(json.dumps(summary["metrics"], indent=2))
    print(f"Results: {results_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
