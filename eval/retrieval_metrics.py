"""Strict, text-match retrieval proxy over a single ranked top-10 result list."""

from typing import Any


def normalize_text(text: str) -> str:
    return " ".join(text.casefold().split())


def evidence_found(passage: str, chunks: list[tuple[float, str]]) -> bool:
    normalized_passage = normalize_text(passage)
    return any(normalized_passage in normalize_text(text) for _, text in chunks)


def score_retrieval(question: dict[str, Any], chunks: list[tuple[float, str]]) -> dict[str, Any]:
    """Rank each quoted passage by its first strict match; no-answer has no relevance label."""
    if question["type"] == "no_answer":
        return {
            "evidence_ranks": [],
            "hit_at_5": None,
            "hit_at_10": None,
            "reciprocal_rank_at_10": None,
            "all_evidence_at_5": None,
            "all_evidence_at_10": None,
        }

    texts = [normalize_text(text) for _, text in chunks[:10]]
    ranks = [
        next((rank for rank, text in enumerate(texts, 1) if normalize_text(passage) in text), None)
        for passage in question["evidence"]
    ]
    found = [rank for rank in ranks if rank is not None]
    return {
        "evidence_ranks": ranks,
        "hit_at_5": any(rank <= 5 for rank in found),
        "hit_at_10": bool(found),
        "reciprocal_rank_at_10": 1 / min(found) if found else 0.0,
        "all_evidence_at_5": (
            all(rank is not None and rank <= 5 for rank in ranks)
            if question["type"] == "multi_hop" else None
        ),
        "all_evidence_at_10": (
            all(rank is not None for rank in ranks)
            if question["type"] == "multi_hop" else None
        ),
    }


def _rate(numerator: float, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def summarize_retrieval(scored: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    answerable = [score for question, score in scored if question["type"] != "no_answer"]
    multi_hop = [score for question, score in scored if question["type"] == "multi_hop"]
    reciprocal_rank_sum = sum(score["reciprocal_rank_at_10"] for score in answerable)
    summary = {}
    for k in (5, 10):
        hits = sum(score[f"hit_at_{k}"] for score in answerable)
        complete = sum(score[f"all_evidence_at_{k}"] for score in multi_hop)
        summary[f"hit_at_{k}"] = {
            "hits": hits, "questions": len(answerable), "rate": _rate(hits, len(answerable)),
        }
        summary[f"multi_hop_all_evidence_at_{k}"] = {
            "complete": complete, "questions": len(multi_hop), "rate": _rate(complete, len(multi_hop)),
        }
    summary["mrr_at_10"] = {
        "reciprocal_rank_sum": reciprocal_rank_sum,
        "questions": len(answerable),
        "rate": _rate(reciprocal_rank_sum, len(answerable)),
    }
    return summary
