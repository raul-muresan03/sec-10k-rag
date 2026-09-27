# Local live API

The FastAPI service answers independent questions about one of the six manifest-verified dev filings. It reads
complete, filing-scoped indexes and calls Ollama for the question embedding and answer. The evaluation replay in
`frontend/` is separate from these live responses.

## Run

From the repository root, install the pipeline, API and test dependencies:

```sh
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r etl_pipeline/requirements.txt -r requirements-api.txt -r requirements-dev.txt
cp .env.example .env
ollama pull nomic-embed-text
ollama pull gemma3:1b
```

The raw SEC submissions must already be at the paths and SHA-256 hashes pinned by `eval/corpus_manifest.v1.json`.
Build the dev indexes once (reruns reuse matching versions), then start the API:

```sh
python3 -m etl_pipeline.filing_store
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

`GET /api/health` checks the process. `GET /api/ready` checks all six verified indexes and both Ollama models;
it returns HTTP 503 if dependencies are missing. `GET /api/filings` lists only prepared dev filings with their
`filing_id`, ticker, company, SEC filing year, and official SEC source URL.

```sh
curl http://127.0.0.1:8000/api/filings
curl -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"filing_id":"1045810-0001045810-26-000021", "question":"How does NVIDIA assign revenue geographically?"}'
```

The JSON answer includes `filing_id`, `model`, `request_id`, `sec_url`, ranked retrieved chunks with scores and
text, and `stage_times_seconds` for retrieval, generation, and the complete request. The evidence and SEC link are
consultable sources; they are not claim-level citations. Each question is independent and there is no persistent
conversation history.

## Configuration and errors

`OLLAMA_BASE_URL` (default `http://localhost:11434`) applies to embedding, model discovery and generation.
`OLLAMA_TIMEOUT_SECONDS` defaults to 120 for embed/generate; model discovery uses five seconds. The server owns
`RAG_MODEL` (`gemma3:1b`), `RAG_TOP_N` (5), and `RAG_MAX_CONCURRENT_GENERATIONS` (1 per API process). Clients cannot
override them per question. The service does not prepare indexes during a chat request.

Invalid requests return 422; an unknown filing ID returns 404. Ollama failure or missing indexes return 503,
generation capacity returns 503, an invalid Ollama response returns 502, and a request timeout returns 504.
Model refusals are successful answers and must be evaluated separately from automatic retrieval metrics.
