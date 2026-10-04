"""Cloud retrieval and generation under one deadline, shared by all callers."""

from collections import OrderedDict
from dataclasses import dataclass
from heapq import nlargest
from threading import Lock
import time

from etl_pipeline.cloud_embeddings import embed
from etl_pipeline.cloud_cosine import cosine
from etl_pipeline.cloud_tokens import validated_input
from etl_pipeline.model_config import ModelConfig
from etl_pipeline.model_errors import ModelInputError
from etl_pipeline.query_deadline import check_deadline
from etl_pipeline.rag_engine import get_llm_response
from etl_pipeline.runtime_snapshot import SnapshotReader


_cache: OrderedDict[tuple[str, str, str], tuple[float, ...]] = OrderedDict()
_cache_lock = Lock()
MAX_CACHE_ENTRIES = 128


@dataclass(frozen=True)
class SnapshotAnswer:
    answer: str | None
    chunks: list[tuple[float, str]]
    metrics: dict
    retrieval_seconds: float
    generation_seconds: float
    total_seconds: float


def retrieve_snapshot(store: SnapshotReader, selected_id: str, question: str, top_n: int,
                      config: ModelConfig, *, deadline: float) -> list[tuple[float, str]]:
    check_deadline(deadline)
    if config.runtime != "cloud":
        raise ValueError("Snapshot retrieval requires cloud embeddings")
    if not 1 <= top_n <= 10 or not question.strip() or len(question.encode("utf-8")) > 2000:
        raise ModelInputError("Cloud question or retrieval count exceeds the input limits")
    question = question.strip()
    validated_input(question, query=True)
    texts, vectors = store.index(selected_id)
    key = (store.snapshot_id, store.embedding_config_id, question)
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
    check_deadline(deadline)
    vector = cached if cached is not None else tuple(embed([question], config, deadline=deadline, query=True)[0])
    check_deadline(deadline)
    with _cache_lock:
        _cache[key] = vector
        _cache.move_to_end(key)
        while len(_cache) > MAX_CACHE_ENTRIES:
            _cache.popitem(last=False)
    scores = []
    for text, candidate in zip(texts, vectors, strict=True):
        check_deadline(deadline)
        score = cosine(vector, candidate)
        scores.append((score, text))
    result = nlargest(top_n, scores)
    check_deadline(deadline)
    return result


def query_snapshot(store: SnapshotReader, selected_id: str, question: str, top_n: int, config: ModelConfig,
                   *, deadline: float | None = None, generate: bool = True) -> SnapshotAnswer:
    started = time.monotonic()
    deadline = started + config.query_timeout_seconds if deadline is None else deadline
    check_deadline(deadline)
    chunks = retrieve_snapshot(store, selected_id, question, top_n, config, deadline=deadline)
    retrieved = time.monotonic()
    check_deadline(deadline)
    answer, metrics = (get_llm_response(question, chunks, config.model, config=config, deadline=deadline)
                       if generate else (None, {}))
    check_deadline(deadline)
    finished = time.monotonic()
    return SnapshotAnswer(answer, chunks, metrics, retrieved - started, finished - retrieved, finished - started)
