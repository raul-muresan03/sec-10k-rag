"""FastAPI entry point for the filing query service."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from api.models import ChatRequest, ChatResponse, FilingSummary
from api.query import QueryService
from api.settings import Settings
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


def create_app(store: FilingIndexStore | None = None, settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="SEC RAG API")
    index_store = store if store is not None else FilingIndexStore()
    config = settings if settings is not None else Settings.from_env()
    query_service = QueryService(index_store, config)

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
        for tag in (EMBEDDING_MODEL, config.model):
            if tag not in names and f"{tag}:latest" not in names:
                return _not_ready(f"Ollama model not installed: {tag}")
        return {"status": "ready"}

    @app.get("/api/filings", response_model=list[FilingSummary])
    def filings() -> list[FilingSummary]:
        try:
            return [
                FilingSummary(
                    filing_id=item.filing_id, ticker=item.ticker,
                    company=COMPANY_NAMES.get(item.ticker, item.ticker),
                    filing_year=item.year, sec_url=item.sec_url,
                )
                for item in index_store.prepared()
            ]
        except (OSError, ValueError, RuntimeError) as error:
            raise HTTPException(status_code=503, detail="Filing indexes unavailable") from error

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        try:
            return query_service.answer(request.filing_id, request.question)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Unknown filing_id") from error
        except OllamaTimeout as error:
            raise HTTPException(status_code=504, detail="Ollama timed out") from error
        except OllamaInvalidResponse as error:
            raise HTTPException(status_code=502, detail="Ollama returned an invalid response") from error
        except OllamaUnavailable as error:
            raise HTTPException(status_code=503, detail="Ollama unavailable") from error
        except (OSError, ValueError, RuntimeError) as error:
            raise HTTPException(status_code=503, detail="Filing index unavailable") from error

    return app


app = create_app()
