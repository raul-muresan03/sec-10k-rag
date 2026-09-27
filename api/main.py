"""FastAPI entry point for the filing query service."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="SEC RAG API")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
