# AGENTS.md

## Project overview
Three Docker services: FastAPI backend (:8000), Streamlit frontend (:8501), ingestion (:8001). Each has its own `requirements.txt`. No Python `__init__.py` files exist — `config.py`, `logger.py`, and `resurse/` live at repo root.

## Commands

```bash
# Full stack (Ollama must already be running on host)
docker compose up --build -d

# Ingest a company (run after stack is up)
docker compose exec ingestion python main.py AAPL 2025

# Rebuild a single service after code changes
docker compose up --build -d --no-deps backend
docker compose up --build -d --no-deps frontend
docker compose up --build -d --no-deps ingestion
```

## Environment
- Config comes only from `config.py` (`pydantic-settings`, reads `.env`).
- **Ollama runs on the host**, not in Docker. Backend and ingestion reach it via `host.docker.internal` (`extra_hosts` in `docker-compose.yml`). Set `OLLAMA_BASE_URL=http://localhost:11434` in `.env`.
- Embeddings always use Ollama `nomic-embed-text` (768-dim). The default LLM is Google `gemini-3.1-flash`.
- `.env.example` is **stale** — lists `LLM_MODEL=gemini-1.5-flash` but the actual default is `gemini-3.1-flash`.
- `resurse/` is in `.gitignore` (local-only TODO and interview prep docs).
- `data/` is in `.gitignore` (logs at `data/logs/app.log`, token DB at `data/token_usage.db`, raw downloads at `data/raw/`). Created automatically.

## Architecture
- **Backend** proxies ingestion: `/ingest` → `http://ingestion:8001/ingest` via httpx.
- **Ingestion** has two entrypoints: CLI (`python main.py TICKER YEAR`) for manual use, FastAPI (`uvicorn api:app --port 8001`) for programmatic use.
- Confidence score is a **custom 4-factor formula** in `rag_engine._calculate_confidence()` — not from any library.
- Retrieval uses `PineconeScoreRetriever` (custom subclass of `BaseRetriever`) that calls `similarity_search_with_score()` to inject raw cosine scores — `as_retriever()` would strip them.
- `sys.path.insert(0, ...)` hacks exist in `etl_pipeline/parser.py`, `chunker.py`, `ingest.py`, `vector_store.py` to import `config` and `logger` from root. **Do not remove without adding proper `__init__.py` and converting imports.**

## Known issues (refactor backlog)
- `parser.py:_clean_html()` — 167 lines, doing 10 things. Split before adding features.
- `rag_engine.py:ask()` — 80 lines. Needs `_single_year_query()` / `_comparison_query()` split.
- `check_pinecone_connection()` in `main.py` violates Law of Demeter (`engine.vector_store.get_pinecone_index(...).describe_index_stats()`). Move into RAGEngine.
- `_extract_10k_document()` can return `None` — caller doesn't check before passing to `_clean_html()`.
- No tests, no CI, no lint/typecheck config. Add before major refactoring.
- Naming: `cs` → `confidence_score`, `u` → `usage`, `dl` → `downloader` in various files.
