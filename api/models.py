"""Public HTTP shapes for verified filings."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FilingSummary(BaseModel):
    filing_id: str
    ticker: str
    company: str
    filing_year: int
    sec_url: str
    status: str = "ready"
    detail: str | None = None


class PreparationResult(BaseModel):
    status: str
    detail: str | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filing_id: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def require_question_text(cls, question: str) -> str:
        if not question.strip():
            raise ValueError("question cannot be blank")
        return question.strip()


class RetrievedChunk(BaseModel):
    rank: int
    score: float
    text: str


class StageTimes(BaseModel):
    retrieval: float
    generation: float
    total: float


class ChatResponse(BaseModel):
    answer: str
    filing_id: str
    model: str
    retrieved_chunks: list[RetrievedChunk]
    sec_url: str
    stage_times_seconds: StageTimes
    request_id: str
