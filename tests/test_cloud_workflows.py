import json
import asyncio
import sys
from unittest.mock import patch

import httpx
import pytest

import ask
from etl_pipeline.runtime_snapshot import SnapshotStore
from etl_pipeline.model_errors import ModelTimeout
from eval.run_eval import run_evaluation


@pytest.fixture
def cloud_environment(monkeypatch, cloud_config, runtime_export):
    for name, value in {
        "RAG_RUNTIME": "cloud", "GROQ_API_KEY": cloud_config.groq_api_key,
        "CLOUDFLARE_API_TOKEN": cloud_config.cloudflare_api_token,
        "CLOUDFLARE_ACCOUNT_ID": cloud_config.cloudflare_account_id,
        "RAG_SNAPSHOT_DIR": str(runtime_export), "OLLAMA_BASE_URL": "not-a-url",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("RAG_MODEL", raising=False)


def cloud_reply(request):
    if request.url.host == "api.cloudflare.com":
        return httpx.Response(200, json={"success": True, "result": {"data": [[1.0] + [0.0] * 383]}})
    return httpx.Response(200, json={"choices": [{
        "finish_reason": "stop", "message": {"content": "Grounded cloud answer"},
    }], "usage": {"total_tokens": 100}})


def test_cloud_cli_queries_read_only_export_without_preparation_or_raw(
    cloud_environment, runtime_export, local_corpus, cloud_http, monkeypatch, capsys,
):
    for filing in local_corpus.catalog().values():
        filing.path.unlink()
    original = {path.name: path.read_bytes() for path in runtime_export.iterdir()}
    monkeypatch.setattr(sys, "argv", ["ask.py", "CLI workflow probe?", "--ticker", "NVDA", "--year", "2026"])
    calls = cloud_http(cloud_reply)
    with patch("requests.post", side_effect=AssertionError("CLI contacted Ollama")):
        ask.main()
    assert "Grounded cloud answer" in capsys.readouterr().out
    assert [request.url.host for request in calls] == ["api.cloudflare.com", "api.groq.com"]
    assert original == {path.name: path.read_bytes() for path in runtime_export.iterdir()}


@pytest.mark.parametrize("workflow", ["cli", "evaluator"])
def test_cloud_workflows_stop_before_generation_when_embedding_consumes_budget(
    cloud_environment, local_corpus, cloud_http, tmp_path, monkeypatch, workflow, capsys,
):
    monkeypatch.setenv("RAG_QUERY_TIMEOUT_SECONDS", "0.2")

    async def slow(request):
        await asyncio.sleep(0.5)
        return cloud_reply(request)

    calls = cloud_http(slow)
    question = f"Deadline {workflow} workflow probe?"
    if workflow == "cli":
        monkeypatch.setattr(sys, "argv", ["ask.py", question, "--ticker", "NVDA", "--year", "2026"])
        with pytest.raises(SystemExit) as failure:
            ask.main()
        assert failure.value.code == 2
        assert "timed out" in capsys.readouterr().err
    else:
        questions = tmp_path / "budget-questions.jsonl"
        questions.write_text(json.dumps({
            "id": "dev-deadline", "split": "dev", "ticker": "NVDA", "year": 2026,
            "type": "narrative", "question": question, "answer": "Grounded cloud answer", "evidence": ["NVDA evidence"],
        }) + "\n")
        with pytest.raises(ModelTimeout):
            run_evaluation("dev", None, 5, "openai/gpt-oss-20b", questions_path=questions,
                           manifest_path=local_corpus.manifest_path, output_directory=tmp_path / "failed-runs")
        assert not (tmp_path / "failed-runs").exists()
    assert [request.url.host for request in calls] == ["api.cloudflare.com"]


def test_cloud_evaluator_uses_frozen_snapshot_without_raw_or_reindexing(
    cloud_environment, runtime_export, local_corpus, cloud_http, tmp_path,
):
    for filing in local_corpus.catalog().values():
        filing.path.unlink()
    questions = tmp_path / "dev-questions.jsonl"
    questions.write_text(json.dumps({
        "id": "dev-cloud-001", "split": "dev", "ticker": "NVDA", "year": 2026,
        "type": "narrative", "question": "Evaluator workflow probe?", "answer": "Grounded cloud answer",
        "evidence": ["NVDA evidence"],
    }) + "\n")
    calls = cloud_http(cloud_reply)
    with patch("requests.post", side_effect=AssertionError("Evaluator contacted Ollama")):
        summary, results, _ = run_evaluation("dev", None, 5, "openai/gpt-oss-20b", questions_path=questions,
                                            manifest_path=local_corpus.manifest_path, output_directory=tmp_path / "runs")
    assert summary["metrics"]["retrieval"]["hit_at_5"]["hits"] == 1
    assert summary["provenance"]["snapshot_id"] == SnapshotStore(runtime_export).snapshot_id
    assert summary["provenance"]["generation_model"]["provider"] == "groq"
    assert json.loads(results.read_text())["provider_metrics"]["usage"]["total_tokens"] == 100
    assert [request.url.host for request in calls] == ["api.cloudflare.com", "api.groq.com"]
