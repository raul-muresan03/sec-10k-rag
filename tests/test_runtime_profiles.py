import json
import sys
from unittest.mock import patch

import pytest

import ask
from api import prepare_filings
from api.main import create_app
from api.settings import Settings
from etl_pipeline.chunker import chunk_10K
from eval.run_eval import run_evaluation


@pytest.fixture
def cloud_environment(monkeypatch, cloud_config):
    monkeypatch.setenv("RAG_RUNTIME", "cloud")
    monkeypatch.delenv("RAG_MODEL", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", cloud_config.groq_api_key)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", cloud_config.cloudflare_api_token)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", cloud_config.cloudflare_account_id)
    monkeypatch.setenv("OLLAMA_BASE_URL", "not-a-url")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "invalid")


def test_cloud_api_settings_do_not_require_ollama_configuration(cloud_environment):
    config = Settings.from_env()
    assert config.model == "openai/gpt-oss-20b"
    assert config.models.runtime == "cloud"
    assert config.models.index_mode == "snapshot"
    assert config.preparation_access == "operator"


def test_cloud_api_cannot_start_with_local_indexes_or_make_startup_requests(cloud_environment, cloud_http):
    calls = cloud_http(lambda request: pytest.fail("Startup contacted a model"))
    with patch("requests.get", side_effect=AssertionError("Startup contacted Ollama")):
        with pytest.raises(RuntimeError, match="Cloud filing snapshots"):
            create_app()
    assert not calls


def test_cloud_cli_refuses_local_index_reuse_before_any_http(cloud_environment, cloud_http, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ask.py", "Revenue?", "--ticker", "NVDA", "--year", "2026"])
    calls = cloud_http(lambda request: pytest.fail("CLI contacted a model before snapshot validation"))
    with patch("requests.get", side_effect=AssertionError("CLI contacted Ollama")):
        with pytest.raises(SystemExit) as failure:
            ask.main()
    assert failure.value.code == 2
    assert "Cloud filing snapshots" in capsys.readouterr().err
    assert not calls


def test_cloud_evaluation_refuses_local_rebuild_before_creating_artifacts(cloud_environment, tmp_path, cloud_http):
    calls = cloud_http(lambda request: pytest.fail("Evaluation contacted a model before snapshot validation"))
    with pytest.raises(RuntimeError, match="Cloud filing snapshots"):
        run_evaluation("dev", 1, 5, "openai/gpt-oss-20b", output_directory=tmp_path / "results")
    assert not (tmp_path / "results").exists()
    assert not calls


def test_cloud_chunker_cannot_rebuild_into_a_local_index(cloud_environment, tmp_path, cloud_http):
    source = tmp_path / "cleaned.txt"
    source.write_text("evidence")
    calls = cloud_http(lambda request: pytest.fail("Legacy chunker contacted a cloud model"))
    with pytest.raises(RuntimeError, match="Cloud filing snapshots"):
        chunk_10K(str(source), output_dir=tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["cleaned.txt"]
    assert not calls


def test_cloud_operator_cli_stops_before_downloading_or_preparing(cloud_environment, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["python -m api.prepare_filings"])
    with patch("requests.get", side_effect=AssertionError("Operator downloaded a filing")):
        with pytest.raises(SystemExit) as failure:
            prepare_filings.main()
    assert failure.value.code == 2
    assert "Cloud filing snapshots" in capsys.readouterr().err


def test_settings_keep_injected_local_model_identity_consistent():
    assert Settings(model="custom-model").models.model == "custom-model"


@pytest.mark.parametrize("name, value", [("FILING_PREPARATION_ACCESS", "browser"), ("RAG_TOP_N", "11")])
def test_cloud_settings_reject_public_preparation_and_unbounded_context(cloud_environment, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        Settings.from_env()
