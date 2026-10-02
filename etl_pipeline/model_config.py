"""Explicit model profiles shared by HTTP, CLI and offline evaluation."""

from dataclasses import dataclass, field
import os
import re
from math import isfinite


CLOUD_GENERATION_MODEL = "openai/gpt-oss-20b"
CLOUD_EMBEDDING_MODEL = "@cf/baai/bge-small-en-v1.5"
CLOUD_EMBEDDING_DIMENSION = 384


@dataclass(frozen=True)
class ModelConfig:
    runtime: str = "local"
    model: str = "gemma3:1b"
    groq_api_key: str = field(default="", repr=False)
    cloudflare_api_token: str = field(default="", repr=False)
    cloudflare_account_id: str = ""
    cloud_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.runtime not in ("local", "cloud"):
            raise ValueError("RAG_RUNTIME must be local or cloud")
        if not self.model.strip():
            raise ValueError("RAG_MODEL must be nonempty")
        if self.runtime == "cloud":
            if not isfinite(self.cloud_timeout_seconds) or not 0 < self.cloud_timeout_seconds <= 30:
                raise ValueError("CLOUD_TIMEOUT_SECONDS must be positive and at most 30")
            if self.model != CLOUD_GENERATION_MODEL:
                raise ValueError(f"Cloud RAG_MODEL must be {CLOUD_GENERATION_MODEL}")
            if not self.groq_api_key:
                raise ValueError("Set GROQ_API_KEY for the cloud profile")
            if not self.cloudflare_api_token:
                raise ValueError("Set CLOUDFLARE_API_TOKEN for the cloud profile")
            if not re.fullmatch(r"[a-f0-9]{32}", self.cloudflare_account_id):
                raise ValueError("CLOUDFLARE_ACCOUNT_ID must be a 32-character hexadecimal account ID")

    @property
    def embedding_model(self) -> str:
        return "nomic-embed-text" if self.runtime == "local" else CLOUD_EMBEDDING_MODEL

    @property
    def generation_provider(self) -> str:
        return "ollama" if self.runtime == "local" else "groq"

    @property
    def embedding_provider(self) -> str:
        return "ollama" if self.runtime == "local" else "cloudflare"

    @property
    def index_mode(self) -> str:
        return "local" if self.runtime == "local" else "snapshot"

    def require_local_indexes(self) -> None:
        if self.index_mode != "local":
            raise RuntimeError("Cloud filing snapshots are not available yet; local Nomic indexes cannot be reused")

    @classmethod
    def from_env(cls, *, runtime: str | None = None, model: str | None = None) -> "ModelConfig":
        selected_runtime = (os.getenv("RAG_RUNTIME", "local") if runtime is None else runtime).strip()
        default_model = CLOUD_GENERATION_MODEL if selected_runtime == "cloud" else "gemma3:1b"
        selected_model = (os.getenv("RAG_MODEL", default_model) if model is None else model).strip()
        if selected_runtime != "cloud":
            return cls(runtime=selected_runtime, model=selected_model)
        try:
            cloud_timeout = float(os.getenv("CLOUD_TIMEOUT_SECONDS", "30"))
        except ValueError:
            raise ValueError("CLOUD_TIMEOUT_SECONDS must be a number") from None
        return cls(runtime=selected_runtime, model=selected_model,
                   groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
                   cloudflare_api_token=os.getenv("CLOUDFLARE_API_TOKEN", "").strip(),
                   cloudflare_account_id=os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip(),
                   cloud_timeout_seconds=cloud_timeout)
