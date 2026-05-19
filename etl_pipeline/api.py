from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from etl_pipeline.main import run_pipeline

app = FastAPI(title="SEC Ingestion API")

class IngestRequest(BaseModel):
    ticker: str
    year: str

@app.post("/ingest")
def ingest_data(request: IngestRequest):
    try:
        run_pipeline(ticker=request.ticker.upper(), year=request.year)
        return {"status": "success", "message": f"Successfully ingested {request.ticker} for {request.year}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
