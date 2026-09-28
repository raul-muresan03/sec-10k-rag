"""One-at-a-time preparation of the manifest-listed dev filings."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from time import monotonic, sleep

from etl_pipeline.chunker import EMBEDDING_MODEL
from etl_pipeline.embedding_model import installed_models
from etl_pipeline.filing_download import download_verified
from etl_pipeline.filing_store import FilingIndexStore
from etl_pipeline.ollama import OllamaInvalidResponse, OllamaTimeout, OllamaUnavailable


@dataclass(frozen=True)
class PreparationStatus:
    status: str
    detail: str | None = None


class PreparationService:
    def __init__(self, store: FilingIndexStore):
        self.store = store
        self._lock = Lock()
        self._states: dict[str, PreparationStatus] = {}
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="filing-preparation")

    def statuses(self) -> dict[str, PreparationStatus]:
        catalog = self.store.catalog()
        with self._lock:
            states = dict(self._states)
        try:
            prepared = {item.filing_id for item in self.store.prepared()}
        except (OllamaUnavailable, OllamaTimeout, OllamaInvalidResponse, RuntimeError):
            prepared = set()
        result = {}
        for selected_id in catalog:
            current = states.get(selected_id, PreparationStatus("unprepared"))
            if current.status in ("queued", "downloading", "waiting_for_models", "indexing"):
                result[selected_id] = current
            elif selected_id in prepared:
                result[selected_id] = PreparationStatus("ready")
            elif current.status == "failed":
                result[selected_id] = current
            else:
                result[selected_id] = PreparationStatus("unprepared")
        return result

    def start(self, selected_id: str) -> PreparationStatus:
        if selected_id not in self.store.catalog():
            raise KeyError(selected_id)
        current = self.statuses()[selected_id]
        if current.status in ("ready", "queued", "downloading", "waiting_for_models", "indexing"):
            return current
        with self._lock:
            current = self._states.get(selected_id)
            if current and current.status in ("queued", "downloading", "waiting_for_models", "indexing"):
                return current
            self._states[selected_id] = PreparationStatus("queued")
            self._executor.submit(self._prepare, selected_id)
        return PreparationStatus("queued")

    def _set(self, selected_id: str, status: str, detail: str | None = None) -> None:
        with self._lock:
            self._states[selected_id] = PreparationStatus(status, detail)

    def _wait_for_model(self) -> None:
        deadline = monotonic() + 1800
        while monotonic() < deadline:
            try:
                names = {model.get("name") for model in installed_models()}
                if EMBEDDING_MODEL in names or f"{EMBEDDING_MODEL}:latest" in names:
                    return
            except (OllamaUnavailable, OllamaTimeout, OllamaInvalidResponse):
                pass
            sleep(5)
        raise RuntimeError("Embedding model did not become available within 30 minutes; check the Ollama logs")

    def _prepare(self, selected_id: str) -> None:
        try:
            filing = self.store.catalog()[selected_id]
            self._set(selected_id, "downloading")
            download_verified(filing)
            self._set(selected_id, "waiting_for_models")
            self._wait_for_model()
            self._set(selected_id, "indexing")
            self.store.prepare_selected(filing.ticker, filing.year)
            self._set(selected_id, "ready")
        except Exception as error:
            self._set(selected_id, "failed", str(error)[:300])
