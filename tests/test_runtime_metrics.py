import pytest

from eval.runtime_metrics import latency_distribution, summarize_ollama, summarize_stage_timings


def test_latency_distribution_preserves_total_and_tail_without_summing_stages():
    distribution = latency_distribution([1.0, 2.0, 3.0, 8.0])

    assert distribution == {
        "count": 4, "total": 14.0, "mean": 3.5,
        "p50": 2.5, "p95": 8.0, "max": 8.0,
    }
    assert latency_distribution([]) == {
        "count": 0, "total": 0.0, "mean": None, "p50": None, "p95": None, "max": None,
    }


def test_stage_timings_keep_indexing_per_filing_and_generation_absent_for_retrieval_only():
    rows = [
        {"latency_seconds": {"retrieval": 0.2, "generation": 1.0}},
        {"latency_seconds": {"retrieval": 0.4, "generation": 2.0}},
    ]
    full = summarize_stage_timings([3.0], rows, include_generation=True)
    retrieval = summarize_stage_timings([3.0], rows, include_generation=False)

    assert full["indexing"]["count"] == 1
    assert full["indexing"]["total"] == 3.0
    assert full["retrieval"]["total"] == pytest.approx(0.6)
    assert full["generation"]["total"] == 3.0
    assert full["indexing_mean"] == 3.0
    assert full["retrieval_mean"] == pytest.approx(0.3)
    assert full["generation_mean"] == 1.5
    assert "generation" not in retrieval and "generation_mean" not in retrieval


def test_ollama_reports_missing_fields_separately_from_zero_and_uses_nanoseconds():
    rows = [
        {"ollama": {
            "prompt_eval_count": 100, "eval_count": 20,
            "total_duration": 1_000_000_000, "eval_duration": 200_000_000,
        }},
        {"ollama": {"prompt_eval_count": 0, "eval_count": 5, "total_duration": 2_000_000_000}},
        {"ollama": {}},
    ]
    reported = summarize_ollama(rows)

    assert reported["prompt_eval_count"] == {
        "unit": "tokens", "reported_questions": 2, "total": 100, "mean_per_reported_question": 50.0,
    }
    assert reported["eval_count"]["total"] == 25
    assert reported["total_duration"]["unit"] == "nanoseconds"
    assert reported["total_duration"]["total"] == 3_000_000_000
    assert reported["eval_duration"]["reported_questions"] == 1
    assert reported["load_duration"]["reported_questions"] == 0
    assert reported["load_duration"]["total"] is None
    assert reported["load_duration"]["mean_per_reported_question"] is None


def test_ollama_rejects_malformed_counters_instead_of_reporting_misleading_totals():
    with pytest.raises(ValueError, match="eval_count"):
        summarize_ollama([{"ollama": {"eval_count": -1}}])
    with pytest.raises(ValueError, match="prompt_eval_duration"):
        summarize_ollama([{"ollama": {"prompt_eval_duration": True}}])
