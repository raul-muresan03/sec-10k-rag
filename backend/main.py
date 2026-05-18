from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from typing import List, Optional
from backend.rag_engine import RAGEngine
from config import settings

app = FastAPI(title="SEC RAG API")

engine = RAGEngine()

class QueryRequest(BaseModel):
    question: str
    namespace: str = "default"

class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    usage: Optional[TokenUsage] = None


def check_pinecone_connection():
    """
    Checks the connection to Pinecone.
    """
    try:
        index_name = engine.index_name
        stats = engine.vector_store.get_pinecone_index(index_name).describe_index_stats()
        return "connected"
    except Exception:
        return "disconnected"

@app.post("/ask", response_model=QueryResponse)
async def ask(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="The question cannot be empty.")

    try:
        result = engine.ask(request.question, namespace=request.namespace)
        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "usage": result.get("usage")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/health")
async def health(response: Response):
    pinecone_status = check_pinecone_connection()
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