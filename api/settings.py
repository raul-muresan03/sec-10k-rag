"""Server-owned answer model and retrieval settings."""

from dataclasses import dataclass
import os

from etl_pipeline.ollama import base_url, timeout_seconds


@dataclass(frozen=True)
class Settings:
    model: str = "gemma3:1b"
    top_n: int = 5

    @classmethod
    def from_env(cls) -> "Settings":
        model = os.getenv("RAG_MODEL", "gemma3:1b").strip()
        top_n = int(os.getenv("RAG_TOP_N", "5"))
        if not model or top_n < 1:
            raise ValueError("RAG_MODEL must be nonempty and RAG_TOP_N must be positive")
        base_url()
        timeout_seconds()
        return cls(model=model, top_n=top_n)
