"""FastAPI entry point for the filing query service."""

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from api.models import ChatRequest, ChatResponse, FilingSummary, PreparationResult
from api.preparation import PreparationService
from api.query import AtCapacity, QueryService
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


def _register_status_routes(app: FastAPI, index_store: FilingIndexStore, config: Settings) -> None:
    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/ready")
    def ready():
        try:
            index_store.catalog()
        except (OSError, ValueError, RuntimeError) as error:
            return _not_ready(f"Filing catalog unavailable: {type(error).__name__}")
        try:
            models = installed_models()
        except (OllamaUnavailable, OllamaTimeout, OllamaInvalidResponse) as error:
            return _not_ready(str(error))
        names = {model.get("name") for model in models}
        for tag in (EMBEDDING_MODEL, config.model):
            if tag not in names and f"{tag}:latest" not in names:
                return _not_ready(f"Ollama model not installed: {tag}")
        return {"status": "ready"}


def _register_filing_route(app: FastAPI, index_store: FilingIndexStore, preparation: PreparationService) -> None:
    @app.get("/api/filings", response_model=list[FilingSummary])
    def filings() -> list[FilingSummary]:
        try:
            statuses = preparation.statuses()
            return [
                FilingSummary(
                    filing_id=selected_id, ticker=item.ticker,
                    company=COMPANY_NAMES.get(item.ticker, item.ticker),
                    filing_year=item.year, sec_url=item.sec_url or "",
                    status=statuses[selected_id].status, detail=statuses[selected_id].detail,
                )
                for selected_id, item in index_store.catalog().items()
            ]
        except (OSError, ValueError, RuntimeError) as error:
            raise HTTPException(status_code=503, detail="Filing catalog unavailable") from error

    @app.post("/api/filings/{filing_id}/prepare", response_model=PreparationResult, status_code=202)
    def prepare(filing_id: str) -> PreparationResult:
        try:
            state = preparation.start(filing_id)
            return PreparationResult(status=state.status, detail=state.detail)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Unknown dev filing_id") from error
        except (OSError, ValueError, RuntimeError) as error:
            raise HTTPException(status_code=503, detail="Filing catalog unavailable") from error


def _register_chat_route(app: FastAPI, query_service: QueryService) -> None:
    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        try:
            with query_service.reserve():
                return await run_in_threadpool(query_service.answer, request.filing_id, request.question)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Unknown filing_id") from error
        except AtCapacity as error:
            raise HTTPException(status_code=503, detail="Generation capacity reached") from error
        except OllamaTimeout as error:
            raise HTTPException(status_code=504, detail="Ollama timed out") from error
        except OllamaInvalidResponse as error:
            raise HTTPException(status_code=502, detail="Ollama returned an invalid response") from error
        except OllamaUnavailable as error:
            raise HTTPException(status_code=503, detail="Ollama unavailable") from error
        except (OSError, ValueError, RuntimeError) as error:
            raise HTTPException(status_code=503, detail="Filing index unavailable") from error


def create_app(store: FilingIndexStore | None = None, settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="SEC RAG API")
    index_store = store if store is not None else FilingIndexStore()
    config = settings if settings is not None else Settings.from_env()
    _register_status_routes(app, index_store, config)
    _register_filing_route(app, index_store, PreparationService(index_store))
    _register_chat_route(app, QueryService(index_store, config))
    return app


app = create_app()
