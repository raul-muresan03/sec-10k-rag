# Local live API

The FastAPI service answers independent questions about one of the six manifest-verified dev filings. It reads
complete, filing-scoped indexes and calls Ollama for the question embedding and answer. Saved evaluation artifacts
under `demo/` and `eval/` are separate from these live responses and are not served by the frontend.

For the Docker Compose workflow (including automatic preparation when a filing is selected), see the
[root README](../README.md).

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
Export the same `.env` settings for index preparation and the API, then build the dev indexes once (reruns reuse
matching versions) and start the API:

```sh
set -a
. ./.env
set +a
python3 -m etl_pipeline.filing_store
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

`GET /api/health` checks the process. `GET /api/ready` checks the dev manifest and both Ollama models;
it returns HTTP 503 if models are still downloading. `GET /api/filings` lists all six dev filings, including those
not yet downloaded, with their `filing_id`, SEC source URL, and preparation `status` and `detail`.
`POST /api/filings/{filing_id}/prepare` queues a verified download and index build, one at a time. It returns 202;
poll `/api/filings` for `queued`, `downloading`, `waiting_for_models`, `indexing`, `ready` or `failed`. Repeating a
request for a queued or ready filing is safe. The raw SEC submission and prepared index persist on disk; job status
is in process memory and an interrupted preparation can be retried. `SEC_API_EMAIL` is required for downloads.
Only manifest-pinned dev IDs are accepted by this endpoint.

With `FILING_PREPARATION_ACCESS=operator`, `/api/filings` lists only prepared filings and the prepare endpoint
always returns 403. This is the intended public application mode; it does not authenticate an operator through
HTTP. The operator uses a shell on the host (and the same named data volume) to prepare a filing instead:

```sh
docker compose run --rm --no-deps api python -m api.prepare_filings --filing-id 1045810-0001045810-26-000021
# Omit --filing-id to prepare every manifest-pinned dev filing.
```

Start Ollama and install both models first (`docker compose up -d ollama models`); set `SEC_API_EMAIL` to a valid
contact address in `.env` before downloading. Run the command from the repository root. The public catalog stays
empty until the first index is ready. Do not expose the Compose development port or leave the default `browser`
mode enabled on an internet-facing service; this setting does not provide TLS, rate limiting, or host security.

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
`FILING_PREPARATION_ACCESS` defaults to `browser` for local use; `operator` disables HTTP preparation and limits
the catalog to ready filings. Invalid values fail at startup.

Invalid requests return 422; an unknown filing ID returns 404. Ollama failure or missing indexes return 503,
generation capacity returns 503, an invalid Ollama response returns 502, and a request timeout returns 504.
Model refusals are successful answers and must be evaluated separately from automatic retrieval metrics.
