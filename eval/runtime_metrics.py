"""Summarize wall-clock stages and Ollama-reported counters without mixing their units."""

from math import ceil, isfinite
import os
import platform
from statistics import median
from typing import Any

from etl_pipeline.rag_engine import OLLAMA_METRIC_FIELDS


def runtime_environment() -> dict[str, str | int | None]:
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "logical_cpu_count": os.cpu_count(),
    }


def latency_distribution(values: list[float]) -> dict[str, float | int | None]:
    if any(not isfinite(value) or value < 0 for value in values):
        raise ValueError("Wall-clock durations must be finite and nonnegative")
    ordered = sorted(values)
    count = len(ordered)
    total = sum(values)
    return {
        "count": count,
        "total": total,
        "mean": total / count if count else None,
        "p50": median(ordered) if count else None,
        "p95": ordered[ceil(0.95 * count) - 1] if count else None,
        "max": ordered[-1] if count else None,
    }


def summarize_stage_timings(
    indexing_seconds: list[float], results: list[dict[str, Any]], include_generation: bool,
) -> dict[str, Any]:
    indexing = latency_distribution(indexing_seconds)
    retrieval = latency_distribution([record["latency_seconds"]["retrieval"] for record in results])
    summary = {
        "indexing_mean": indexing["mean"],
        "retrieval_mean": retrieval["mean"],
        "indexing": indexing,
        "retrieval": retrieval,
    }
    if include_generation:
        generation = latency_distribution([record["latency_seconds"]["generation"] for record in results])
        summary["generation_mean"] = generation["mean"]
        summary["generation"] = generation
    return summary


def summarize_ollama(results: list[dict[str, Any]]) -> dict[str, dict[str, str | int | float | None]]:
    reported = {}
    for field in OLLAMA_METRIC_FIELDS:
        values = []
        for record in results:
            metrics = record.get("ollama", {})
            if not isinstance(metrics, dict):
                raise ValueError("Ollama metrics must be a mapping")
            if field not in metrics:
                continue
            value = metrics[field]
            if type(value) is not int or value < 0:
                raise ValueError(f"Invalid Ollama {field}: expected a nonnegative integer")
            values.append(value)
        reported[field] = {
            "unit": "nanoseconds" if field.endswith("duration") else "tokens",
            "reported_questions": len(values),
            "total": sum(values) if values else None,
            "mean_per_reported_question": sum(values) / len(values) if values else None,
        }
    return reported
