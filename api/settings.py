"""Server-owned answer model and retrieval settings."""

from dataclasses import dataclass, field, replace
import os
from typing import Literal

from etl_pipeline.ollama import base_url, timeout_seconds
from etl_pipeline.model_config import ModelConfig


@dataclass(frozen=True)
class Settings:
    model: str = "gemma3:1b"
    top_n: int = 5
    max_concurrent_generations: int = 1
    preparation_access: Literal["browser", "operator"] = "browser"
    models: ModelConfig = field(default_factory=ModelConfig, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "models", replace(self.models, model=self.model))
        if not self.model or self.top_n < 1 or self.max_concurrent_generations < 1:
            raise ValueError("RAG_MODEL must be nonempty; RAG_TOP_N and generation capacity must be positive")
        if self.preparation_access not in ("browser", "operator"):
            raise ValueError("FILING_PREPARATION_ACCESS must be browser or operator")
        if self.models.runtime == "cloud":
            if self.preparation_access != "operator":
                raise ValueError("Cloud FILING_PREPARATION_ACCESS must be operator")
            if self.top_n > 10:
                raise ValueError("Cloud RAG_TOP_N must be at most 10")

    @classmethod
    def from_env(cls) -> "Settings":
        models = ModelConfig.from_env()
        model = models.model
        top_n = int(os.getenv("RAG_TOP_N", "5"))
        capacity = int(os.getenv("RAG_MAX_CONCURRENT_GENERATIONS", "1"))
        default_access = "operator" if models.runtime == "cloud" else "browser"
        preparation_access = os.getenv("FILING_PREPARATION_ACCESS", default_access).strip().lower()
        if models.runtime == "local":
            base_url()
            timeout_seconds()
        return cls(model=model, top_n=top_n, max_concurrent_generations=capacity,
                   preparation_access=preparation_access, models=models)
