"""One independent filing question through retrieval and Ollama generation."""

from contextlib import contextmanager
import time
from threading import BoundedSemaphore
from uuid import uuid4

from api.models import ChatResponse, RetrievedChunk, StageTimes
from api.settings import Settings
from etl_pipeline.filing_store import FilingIndexStore
from etl_pipeline.rag_engine import get_llm_response
from etl_pipeline.vector_store import get_most_similar_chunks


class AtCapacity(RuntimeError):
    pass


class QueryService:
    def __init__(self, store: FilingIndexStore, settings: Settings):
        self.store = store
        self.settings = settings
        self.generation_slots = BoundedSemaphore(settings.max_concurrent_generations)

    @contextmanager
    def reserve(self):
        if not self.generation_slots.acquire(blocking=False):
            raise AtCapacity("Generation capacity reached")
        try:
            yield
        finally:
            self.generation_slots.release()

    def answer(self, filing_id: str, question: str) -> ChatResponse:
        started = time.perf_counter()
        filing = self.store.resolve_id(filing_id)

        retrieval_start = time.perf_counter()
        chunks = get_most_similar_chunks(question, self.settings.top_n, filing.index_path)
        retrieval_seconds = time.perf_counter() - retrieval_start

        generation_start = time.perf_counter()
        answer, _ = get_llm_response(question, chunks, self.settings.model)
        generation_seconds = time.perf_counter() - generation_start

        return ChatResponse(
            answer=answer, filing_id=filing.filing_id, model=self.settings.model,
            retrieved_chunks=[
                RetrievedChunk(rank=rank, score=score, text=text)
                for rank, (score, text) in enumerate(chunks, start=1)
            ],
            sec_url=filing.sec_url,
            stage_times_seconds=StageTimes(
                retrieval=retrieval_seconds, generation=generation_seconds,
                total=time.perf_counter() - started,
            ),
            request_id=str(uuid4()),
        )
