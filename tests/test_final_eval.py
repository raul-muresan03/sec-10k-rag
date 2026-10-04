"""Final test-split evaluation against frozen offline indexes, never the public export."""

import json

import httpx
import pytest

from eval.cloud_eval import evaluate_snapshot
from eval.final_eval import FrozenTestIndexes, assert_frozen_behavior, run_final_test_evaluation
from tests.filing_helpers import filing_corpus


def test_split_questions(tmp_path):
    path = tmp_path / "questions.jsonl"
    records = []
    for number, (ticker, year) in enumerate((("NVDA", 2026), ("F", 2014))):
        records.append({
            "id": f"final-{number}", "split": "test", "ticker": ticker, "year": year,
            "type": "narrative", "question": f"Final probe {ticker}?",
            "answer": f"{ticker} evidence", "evidence": [f"{ticker} evidence"],
        })
    path.write_text("".join(json.dumps(record) + "\n" for record in records))
    return path


def providers(request):
    if request.url.host == "api.cloudflare.com":
        return httpx.Response(200, json={"success": True, "result": {"data": [
            [1.0] + [0.0] * 383 for _ in json.loads(request.content)["text"]
        ]}})
    return httpx.Response(200, json={"choices": [{
        "finish_reason": "stop", "message": {"content": "Grounded final answer"},
    }], "usage": {"total_tokens": 10}})


def test_split_requires_final_mode_with_explicit_indexes(tmp_path, cloud_config):
    with pytest.raises(ValueError, match="reserved for final"):
        evaluate_snapshot("test", None, 5, cloud_config, tmp_path / "q.jsonl",
                          tmp_path / "m.json", "retrieval-only")
    with pytest.raises(ValueError, match="reserved for final"):
        evaluate_snapshot("test", None, 5, cloud_config, tmp_path / "q.jsonl", tmp_path / "m.json",
                          "retrieval-only", None, 0.0, True)


def test_final_evaluation_reads_frozen_test_indexes_only(tmp_path, cloud_config, cloud_http):
    local_corpus = filing_corpus(tmp_path / "corpus", split="test")
    cloud_http(providers)
    questions = test_split_questions(tmp_path)
    manifest_path = local_corpus.manifest_path
    store = FrozenTestIndexes(manifest_path, tmp_path / "cache", cloud_config, None)
    assert {filing.ticker for filing in store.prepared()} == {"NVDA", "F"}
    assert all(entry["split"] == "test" for entry in store.manifest["filings"])
    payload, records = evaluate_snapshot("test", None, 5, cloud_config, questions, manifest_path,
                                         "retrieval-only", store, 0.0, True)
    assert payload["split"] == "test"
    assert payload["run_id"].endswith("-test-cloud")
    assert len(records) == 2
    assert payload["provenance"]["snapshot_id"] == store.snapshot_id
    assert not (tmp_path / "export").exists()


def test_final_runner_writes_artifacts_without_a_public_export(tmp_path, cloud_config, cloud_http):
    local_corpus = filing_corpus(tmp_path / "corpus", split="test")
    cloud_http(providers)
    payload, results_path, summary_path = run_final_test_evaluation(
        5, cloud_config, test_split_questions(tmp_path), local_corpus.manifest_path,
        tmp_path / "runs", tmp_path / "cache", 0.0)
    assert payload["metrics"]["questions"] == 2
    assert payload["metrics"]["provider_usage"]["total_tokens"] == 20
    assert results_path.is_file() and summary_path.is_file()


def test_frozen_contract_matches_current_indexing_behavior():
    contract = assert_frozen_behavior()
    assert len(contract["snapshot_id"]) == 64
    assert len(contract["index_config_id"]) == 64


def test_frozen_contract_rejects_behavior_drift(monkeypatch):
    import eval.final_eval as final_eval

    def drifted():
        from etl_pipeline.cloud_identity import index_configuration

        identity = index_configuration()
        return {**identity, "chunking": {**identity["chunking"], "max_characters": 1}}

    monkeypatch.setattr(final_eval, "index_configuration", drifted)
    with pytest.raises(ValueError, match="drifted from the frozen contract"):
        assert_frozen_behavior()
