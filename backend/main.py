from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from typing import List, Optional
from backend.rag_engine import RAGEngine
from config import settings
import os
import httpx

app = FastAPI(title="SEC RAG API")

engine = RAGEngine()

class QueryRequest(BaseModel):
    question: str
    namespace: str = "default"
    compare_year: Optional[str] = None
    provider: str = "google"
    model_name: str = "gemini-3.1-flash"

class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    usage: Optional[TokenUsage] = None
    confidence_score: float = 0.0

class IngestRequest(BaseModel):
    ticker: str
    year: str

@app.post("/ask", response_model=QueryResponse)
async def ask(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="The question cannot be empty.")

    try:
        result = engine.ask(
            query=request.question,
            namespace=request.namespace,
            compare_year=request.compare_year,
            provider=request.provider,
            model_name=request.model_name
        )
        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "usage": result.get("usage"),
            "confidence_score": result.get("confidence_score", 0.0)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/health")
async def health(response: Response):
    pinecone_status = "connected" if engine.check_connection() else "disconnected"
    google_api = "configured" if settings.google_api_key else "missing"

    is_healthy = pinecone_status == "connected" and google_api == "configured"

    if not is_healthy:
        response.status_code = 503
        status_label = "degraded"
    else:
        status_label = "online"

    return {
        "status": status_label,
        "checks": {
            "pinecone": pinecone_status,
            "google_ai": google_api
        }
    }

@app.post("/ingest")
async def ingest(request: IngestRequest):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://ingestion:8001/ingest",
                json={"ticker": request.ticker, "year": request.year},
                timeout=120.0
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Ingestion service unavailable: {str(exc)}")

@app.get("/companies")
async def get_companies():
    base_path = "data/raw/sec-edgar-filings"
    default_companies = ["AAPL", "TSLA", "GOOGL", "NVDA"]
    if not os.path.exists(base_path):
        return default_companies

    tickers = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    all_tickers = sorted(list(set(tickers + default_companies)))
    return all_tickers

@app.get("/models")
async def get_models():
    models = {
        "Cloud": {
            "google": [],
            "openai": [],
            "anthropic": []
        },
        "Local": {
            "ollama": []
        }
    }

    if settings.google_api_key:
        models["Cloud"]["google"] = ["gemini-2.5-flash-lite", "gemini-3.1-flash", "gemini-3.1-pro"]

    if settings.openai_api_key:
        models["Cloud"]["openai"] = ["gpt-5.4-nano", "gpt-5.4-mini", "o4-mini", "gpt-5.4", "o3"]

    if settings.anthropic_api_key:
        models["Cloud"]["anthropic"] = ["claude-haiku-4.5", "claude-sonnet-4.6", "claude-opus-4.7"]

    async with httpx.AsyncClient() as client:
        try:
            ollama_url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
            response = await client.get(ollama_url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                models["Local"]["ollama"] = [model["name"] for model in data.get("models", [])]
        except Exception:
            pass

    return models
