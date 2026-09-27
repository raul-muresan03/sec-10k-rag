"""FastAPI entry point for the filing query service."""

from fastapi import FastAPI

from api.models import FilingSummary
from etl_pipeline.filing_store import FilingIndexStore


COMPANY_NAMES = {
    "ADBE": "Adobe", "AMZN": "Amazon", "F": "Ford", "NVDA": "NVIDIA",
    "PFE": "Pfizer", "SBUX": "Starbucks",
}


def create_app(store: FilingIndexStore | None = None) -> FastAPI:
    app = FastAPI(title="SEC RAG API")
    index_store = store if store is not None else FilingIndexStore()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

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
