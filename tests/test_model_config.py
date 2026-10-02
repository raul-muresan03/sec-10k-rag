import pytest

from etl_pipeline.model_config import ModelConfig


def test_default_profile_preserves_local_ollama(monkeypatch):
    monkeypatch.delenv("RAG_RUNTIME", raising=False)
    monkeypatch.delenv("RAG_MODEL", raising=False)
    config = ModelConfig.from_env()
    assert config.runtime == "local"
    assert config.model == "gemma3:1b"
    assert config.embedding_model == "nomic-embed-text"
    assert config.generation_provider == config.embedding_provider == "ollama"


def test_cloud_profile_selects_approved_models_and_hides_credentials(monkeypatch):
    monkeypatch.setenv("RAG_RUNTIME", "cloud")
    monkeypatch.delenv("RAG_MODEL", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "private-groq-key")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "private-cloudflare-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a" * 32)
    config = ModelConfig.from_env()
    assert config.model == "openai/gpt-oss-20b"
    assert config.embedding_model == "@cf/baai/bge-small-en-v1.5"
    assert config.generation_provider == "groq"
    assert config.embedding_provider == "cloudflare"
    assert "private-" not in repr(config)


@pytest.mark.parametrize("overrides, message", [
    ({"RAG_RUNTIME": "hybrid"}, "RAG_RUNTIME"),
    ({"RAG_RUNTIME": ""}, "RAG_RUNTIME"),
    ({"RAG_MODEL": ""}, "RAG_MODEL"),
    ({"RAG_MODEL": "paid-model"}, "RAG_MODEL"),
    ({"GROQ_API_KEY": ""}, "GROQ_API_KEY"),
    ({"CLOUDFLARE_API_TOKEN": ""}, "CLOUDFLARE_API_TOKEN"),
    ({"CLOUDFLARE_ACCOUNT_ID": "../untrusted"}, "CLOUDFLARE_ACCOUNT_ID"),
])
def test_cloud_configuration_fails_closed(monkeypatch, overrides, message):
    for name, value in {
        "RAG_RUNTIME": "cloud", "RAG_MODEL": "openai/gpt-oss-20b",
        "GROQ_API_KEY": "private-groq-key", "CLOUDFLARE_API_TOKEN": "private-cloudflare-token",
        "CLOUDFLARE_ACCOUNT_ID": "a" * 32, **overrides,
    }.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=message) as failure:
        ModelConfig.from_env()
    assert "private-" not in str(failure.value)


@pytest.mark.parametrize("timeout", ["0", "nan", "inf", "31"])
def test_cloud_timeout_must_fit_the_request_budget(monkeypatch, timeout, cloud_config):
    monkeypatch.setenv("RAG_RUNTIME", "cloud")
    monkeypatch.setenv("GROQ_API_KEY", cloud_config.groq_api_key)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", cloud_config.cloudflare_api_token)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", cloud_config.cloudflare_account_id)
    monkeypatch.setenv("CLOUD_TIMEOUT_SECONDS", timeout)
    with pytest.raises(ValueError, match="CLOUD_TIMEOUT_SECONDS"):
        ModelConfig.from_env()
