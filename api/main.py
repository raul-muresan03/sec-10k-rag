"""FastAPI entry point for the filing query service."""

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from api.models import FilingSummary
from etl_pipeline.chunker import EMBEDDING_MODEL
from etl_pipeline.embedding_model import installed_models
from etl_pipeline.filing_store import FilingIndexStore
from etl_pipeline.ollama import OllamaInvalidResponse, OllamaTimeout, OllamaUnavailable


COMPANY_NAMES = {
    "ADBE": "Adobe", "AMZN": "Amazon", "F": "Ford", "NVDA": "NVIDIA",
    "PFE": "Pfizer", "SBUX": "Starbucks",
}


def _not_ready(reason: str) -> JSONResponse:
    return JSONResponse(status_code=503, content={"status": "not_ready", "reason": reason})


def create_app(store: FilingIndexStore | None = None) -> FastAPI:
    app = FastAPI(title="SEC RAG API")
    index_store = store if store is not None else FilingIndexStore()
    generation_model = os.getenv("RAG_MODEL", "gemma3:1b")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/ready")
    def ready():
        try:
            prepared = index_store.prepared()
        except (OSError, ValueError, RuntimeError) as error:
            return _not_ready(f"Filing indexes unavailable: {type(error).__name__}")
        if len(prepared) != 6:
            return _not_ready("Six verified dev filing indexes are required")
        try:
            models = installed_models()
        except (OllamaUnavailable, OllamaTimeout, OllamaInvalidResponse) as error:
            return _not_ready(str(error))
        names = {model.get("name") for model in models}
        for tag in (EMBEDDING_MODEL, generation_model):
            if tag not in names and f"{tag}:latest" not in names:
                return _not_ready(f"Ollama model not installed: {tag}")
        return {"status": "ready"}

    @app.get("/api/filings", response_model=list[FilingSummary])
    def filings() -> list[FilingSummary]:
        return [
            FilingSummary(
                filing_id=item.filing_id, ticker=item.ticker,
                company=COMPANY_NAMES.get(item.ticker, item.ticker),
                filing_year=item.year, sec_url=item.sec_url,
            )
            for item in index_store.prepared()
        ]

    return app


app = create_app()
