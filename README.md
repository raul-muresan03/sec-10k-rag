# SEC 10-K RAG

Live demo: **https://sec-10k-rag-rauls-projects-2096a6fa.vercel.app** — chat over six prepared 10-K filings,
served as one Vercel project (Vite frontend + FastAPI backend) with Groq generation and Cloudflare embeddings.
No accounts, no history, no database; each question is answered independently from a frozen, checksummed index
snapshot (`9b77d199…4e00d8`).

Locally the same repository runs a complete SEC 10-K RAG pipeline with a live FastAPI endpoint. It verifies
manifest-listed filings, persists separate indexes per filing, retrieves relevant chunks with cosine similarity,
and generates answers through Ollama. The frontend is a filing-scoped chat; saved evaluation results remain
internal to the repository.

The backend uses local files without a vector database or orchestration framework.

## Screenshots & demo

Media lives under `docs/` (tracked). Fill the TODOs below with real captures from the live URL:

- [x] `docs/screenshot-chat.png` — chat answering a question with retrieved passages and the SEC source link
- [x] `docs/demo_final.mp4` — 2-minute walkthrough: select a filing, ask a revenue question, show the evidence
- [x] `docs/architecture.png` ([source](docs/architecture.svg)) — one-origin diagram: browser → Vercel services → frozen export + Groq/Cloudflare

## What I built myself
- Implemented the pipeline and product code by hand across the roadmap (SEC parsing/cleaning, semantic chunking,
  cosine retrieval, RAG orchestration, FastAPI backend, chat UI, evaluation harness with rubric and owner review).
- A decision made against the grain: [..] — e.g. keeping the public bundle to six dev filings with test filings
  indexed strictly offline, or accepting per-instance generation limits over new infrastructure.
- Operated the deployment end to end: Vercel project and secrets, staged candidates, smoke checks, controlled
  promotion, and the key-rotation/exposure hygiene around them.

## Current Scope

Implemented:

- Download the newest 10-K filed in a requested year with `sec-edgar-downloader`
- Extract a document block from an SEC submission
- Remove hidden and noisy HTML and convert tables to Markdown-like text
- Build semantic chunks from adjacent paragraphs
- Generate embeddings in batches with Ollama's `nomic-embed-text` model
- Store verified, versioned filing-scoped indexes locally in JSON
- Retrieve chunks with brute-force cosine similarity
- Generate an answer with a local Ollama model
- Select explicit local/cloud model profiles; test Groq generation and Cloudflare embedding adapters offline
- Answer filing-scoped questions through the [live API](api/README.md) or the chat interface
- Serve the public demo from Vercel with explicit cloud providers and a verified read-only index snapshot
- Publish controlled releases: CI-gated staged candidates, pre-promotion smoke, exact-artifact promotion, rollback
- Validate saved dev answers, evidence, and retrieval metrics in internal evaluation artifacts
- Run the final test-split evaluation on frozen offline indexes with full provenance (16 questions, 4 filings)
- Prepare the six dev filings with `python3 -m etl_pipeline.filing_store` or prepare one through `ask.py`
- Log questions, answers, retrieved chunks, latency, and Ollama metrics as JSONL
- Run the frontend, API and Ollama together with Docker Compose; open a dev filing from the chat interface

Not implemented:

- Claim-level citations to exact locations in a filing (the interface shows source passages and a link to the full filing)
- Confidence scores or similarity thresholds
- Cross-filing, multi-company, or year-over-year answers; each query selects one filing
- Per-user rate limiting (per-instance generation cap plus fail-closed Free quotas instead)
- Pinecone, LangChain, or hybrid search

## How It Works

```text
Manifest-verified SEC EDGAR submission
  -> parse -> clean HTML/tables -> chunk -> embed with Ollama
  -> data/indexes/<CIK>-<ACCESSION>/<INDEX_VERSION>/all_chunks_embeddings.json
Question -> embed -> cosine similarity in selected filing -> top N chunks
  -> Ollama generation -> CLI or API answer
```

Each query loads the selected filing's chunks and embeddings and compares them to its question embedding.
Index preparation keeps intermediate artifacts in a temporary directory rather than changing `etl_pipeline.DATA_DIR`.

```text
Public demo: browser -> Vercel services (web + api)
  api reads deploy/indexes (frozen) -> Cloudflare embeds the question
  -> cosine retrieval -> Groq openai/gpt-oss-20b answers
Laptop prepares indexes offline; GitHub main + green CI publishes staged candidates after smoke.
```

## Requirements

- Python 3.12 recommended (cloud adapters require Python 3.11 or newer)
- [Ollama](https://ollama.com/) running at `http://localhost:11434`
- The manifest-listed raw filings at their recorded `data/sec-edgar-filings/` paths
- Network access and a contact email only when obtaining SEC submissions separately
- `nomic-embed-text` for indexing and retrieval
- `gemma3:1b` by default for answer generation, or another installed Ollama model selected with `--model`

## Docker Compose (simplest local start)

Install Docker with the Compose plugin. Set your SEC contact address in `.env` before first use:

```bash
cp .env.example .env
# Edit SEC_API_EMAIL in .env.
```

From a clone of this repository:

```bash
docker compose up
```

Open **http://localhost:8080**. The app lists the six manifest-pinned *dev* filings even on a clean install. Choosing
one starts preparation automatically: the API downloads the exact SEC submission, verifies its checksum and identity,
and builds its index. The UI shows when the filing is being opened; on CPU, the first index can take a while. Two Ollama
models (`nomic-embed-text` and `gemma3:1b`) are downloaded automatically in the background on the first start.
They require internet access and several gigabytes of disk space. Chat becomes available for each filing as soon as
its index is ready. Do not commit `.env`.

If you edit `.env` after starting, apply it with `docker compose up -d --force-recreate api`. The API only downloads
the six pinned dev filings; it rejects a mismatched SHA-256 or SEC header. The 16 test questions and their filings
are not part of this flow. If preparation fails, use **Try again** beside the selected filing; if its status cannot
be checked, use **Check again**. Only the web port is exposed, bound to localhost by default; the API and Ollama are
internal Compose services.

`FILING_PREPARATION_ACCESS=operator` changes the API to list only prepared filings and return 403 for all HTTP
preparation requests. Prepare from an operator shell as described in [api/README.md](api/README.md). If no filing
has been prepared, the chat view says so. This is a component of public deployment, **not** a complete public
configuration: the Compose default still binds the web port to localhost and does not set up HTTPS or request
rate limits. Do not expose the development setup to the internet by changing `WEB_BIND_ADDRESS` alone.

Subsequent starts use the same `docker compose up` (add `-d` for background, or `--build` after code changes)
and stop with:

```bash
docker compose down
```

Verify each layer as you go (localhost):

```bash
curl http://127.0.0.1:8000/api/health                       # {"status":"ok"} — process is up
curl http://127.0.0.1:8000/api/ready                        # {"status":"ready"} or 503 while models download
curl http://127.0.0.1:8000/api/filings | python3 -m json.tool  # six filings with preparation statuses
```

Compose exposes only the web port; the API port above works when you run the API natively
(`python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000`).

### Cloud profile on your machine

You need free Groq and Cloudflare accounts (no billing, no paid fallback). Export the backend-only variables
from [MODEL_PROVIDERS.md](MODEL_PROVIDERS.md), then prepare one filing into an ignored directory and query it:

```sh
export RAG_RUNTIME=cloud RAG_MODEL=openai/gpt-oss-20b FILING_PREPARATION_ACCESS=operator
export GROQ_API_KEY=... CLOUDFLARE_API_TOKEN=... CLOUDFLARE_ACCOUNT_ID=...
python -m etl_pipeline.cloud_indexing --ticker NVDA --year 2026 --output /tmp/opencode/cloud-candidate
RAG_SNAPSHOT_DIR=/tmp/opencode/cloud-candidate python ask.py 'How does NVIDIA assign revenue geographically?' \
  --ticker NVDA --year 2026
```

### Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `/api/ready` is 503 `Ollama model not installed` | models still downloading | wait, then `docker compose logs models` |
| Chat answers 503 `Filing index unavailable` | filing not prepared yet | pick it in the UI and wait for `ready`, or prepare via CLI |
| Chat answers 429 | shared Free quota exhausted | wait for reset; do not hammer retry — it prolongs the outage |
| Chat answers 504 | provider timeout | retry once manually; lower `RAG_QUERY_TIMEOUT_SECONDS` if frequent |
| `prepare` returns 403 | operator-only mode (cloud default) | prepare from an operator shell, not HTTP |
| `Snapshot ... checksum mismatch` at startup | code changed after the export was built | rebuild the export with `python -m etl_pipeline.cloud_indexing --output deploy/indexes` into a new directory |
| Port 8080 taken | another service | set `WEB_PORT` in `.env` |
| `npm run build` fails on Node < 22 | wrong toolchain | use Node 22 (`frontend/.nvmrc`, `engines` pin) |

The `filings` and `ollama_models` named volumes persist across `down` and image rebuilds; don't use `down -v` unless
you intend to delete downloaded filings, indexes and models. Configure `WEB_PORT` in `.env` if port 8080 is taken.
`GET http://localhost:8080/api/health` checks the API process; `/api/ready` reports when both Ollama models are
available. `/api/filings` shows each filing's preparation status. To see model-pull or API errors, run
`docker compose logs models api ollama`. Internal evaluation artifacts remain independent of live preparation.

Local CPU smoke on a 16-thread Ryzen 7 7435HS with 23 GiB RAM (2026-09-28): an NVDA index took about 131 seconds
once model downloads finished; a live NVDA question took 5.18 seconds and returned five passages. During indexing,
Ollama briefly used about 800% CPU (eight cores); after the query, the three running containers used about 1.9 GiB
of RAM. The one-filing data volume used 17 MiB and the two-model volume 1.1 GiB; the Ollama container image itself
occupied about 10.6 GB locally. These are observations from one machine, not a VPS sizing target.

The commands below describe the alternative native Python/Vite setup.

## Model profiles

`RAG_RUNTIME=local` is the default; Compose explicitly uses this profile. Ollama remains responsible for indexing,
question embeddings and generation. Native Python commands read exported environment variables, not `.env` automatically.
`RAG_MODEL` now sets the CLI default as well as the API; `--model` overrides it for CLI/evaluation.

The explicit `cloud` profile selects Groq `openai/gpt-oss-20b` and Cloudflare `@cf/baai/bge-small-en-v1.5`.
It never falls back to Ollama or a different model. The public runtime reads the frozen export selected by
`RAG_SNAPSHOT_DIR` (default `deploy/indexes`); API, CLI and evaluation share one absolute query deadline
(`RAG_QUERY_TIMEOUT_SECONDS`, default 60). See [MODEL_PROVIDERS.md](MODEL_PROVIDERS.md) for configuration, bounds
and errors, [CLOUD_INDEXES.md](CLOUD_INDEXES.md) for the snapshot contract, and [VERCEL.md](VERCEL.md) for packaging,
controlled releases and recovery.

## Frozen release and final evaluation

Frozen behavior contract: [`eval/frozen_behavior.v1.json`](eval/frozen_behavior.v1.json) (BGE tokenizer, 480 content /
512 final tokens, mean pooling, 384 dimensions, token-bounded adjacent-cosine chunking). The final test evaluation
refuses to run on any drift. Public snapshot `9b77d19945eb0d8000d1137d5be2ff6ffda03c8ea7e5f641ee4298039f4e00d8`:
six dev filings, 2,869 chunks, 4.812 MiB compressed / 21.325 MiB expanded.

Cloud scores are new measurements, not a rename of the historical Ollama evaluations:

| Run | Split | Retrieval hit@5 | Multi-hop complete | No-answer correct | Notes |
| --- | --- | --- | --- | --- | --- |
| `20261002T133927181691Z-dev-cloud` | dev, 24 q | 15/18 | 6/6 | — (retrieval-only) | top-10; misses: nvda narrative, sbux numeric, f narrative |
| `20261004T162542904468Z-test-cloud` | test, 16 q | 10/12 | 3/4 | 4/4, 0 false | top-5, full generation; ~29K tokens; retrieval mean 0.41 s, generation mean 0.72 s |

The 16 test questions target four filings (AAPL 2024, CVX 2019, JPM 2023, WMT 2014) indexed separately offline with
the frozen configuration; they were never exported, published, or served. Historical Ollama dev baseline
(`eval/reviews/dev_baseline.v1.json`, run `20260923T125212753976Z-dev`): 11 pass / 6 partial / 7 incorrect with all
four medium-confidence Adobe/Pfizer verdicts owner-confirmed. No question labels were changed to mask regressions.

Reproduce the export offline (needs the approved cloud environment; writes only to ignored directories):

```sh
python -m etl_pipeline.cloud_indexing --output /tmp/opencode/snapshot-check
python -m eval.final_eval --question-interval-seconds 61
```

Quotas are fail-closed Free on both providers; a burst silences the demo until reset, and no rollback fixes that.
Back up `deploy/indexes/` with its manifest before any reindexing; a reindex never rewrites history in place.

## Setup

Run all commands from the repository root.

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r etl_pipeline/requirements.txt -r requirements-api.txt -r requirements-dev.txt
cp .env.example .env
```

If downloading additional SEC filings, set the SEC EDGAR contact email in `.env`:

```ini
SEC_API_EMAIL=your_email@example.com
```

Install and start Ollama, then pull the models used by the application:

```bash
ollama pull nomic-embed-text
ollama pull gemma3:1b
```

## Prepare Filing Indexes

`eval/corpus_manifest.v1.json` pins the filing paths, accessions, SEC URLs and source SHA-256s. Place the six dev
submissions at those exact paths before preparing indexes. The test-split filings are reserved for final evaluation.
Preparation verifies every dev filing before building any index:

```bash
python3 -m etl_pipeline.filing_store
```

Each index is built in a temporary directory and published under
`data/indexes/<CIK>-<ACCESSION>/<INDEX_VERSION>/` after validation. A rerun reuses complete matching indexes; an
interrupted build leaves no published partial index. Source, preprocessing or Ollama embedding-model digest changes
select a new index version. `ask.py` can prepare one selected dev filing if it is missing, without downloading it.

`--year` means the SEC filing year, not the fiscal year. The CLI accepts only manifest-verified dev filings.

The embedding request batch size defaults to `512`. Changing it selects a new index version:

```bash
EMBEDDING_BATCH_SIZE=128 python3 -m etl_pipeline.filing_store
```

## Ask Questions

Ask about a 10-K filed in a specific year:

```bash
python3 ask.py --ticker NVDA --year 2026 "Who is the CEO of NVIDIA?"
```

Select an SEC filing year, retrieval count, and generation model:

```bash
python3 ask.py --ticker NVDA --year 2026 --top-n 3 --model gemma3:1b "What risks does the company describe?"
```

The CLI prints indexing progress when rebuilding, the selected index path, retrieval time, generation time, and final
answer. The default values are `--top-n 5` and `--model gemma3:1b`.

Each completed query appends one record to `data/query_log.jsonl`. Records include the ticker, filing year,
question, answer, model, retrieved chunk text and scores, retrieval and generation latency, and the token counts and
durations returned by Ollama. Ollama duration fields are stored unchanged in nanoseconds.

To ask through HTTP, see the [API runbook](api/README.md). The API does not append to the CLI query log.

To ask through the Chat UI, start the API, then run the frontend dev server (it proxies `/api` to
`http://127.0.0.1:8000`):

```bash
npm --prefix frontend ci
npm --prefix frontend run dev -- --port 5173
```

The frontend presents only the live chat. Changing filings starts a new conversation; questions in the same filing
appear together, but each answer is generated independently and the conversation clears on refresh. In production the
same origin serves the UI and reverse-proxies `/api`. The dev replay snapshot lives under `demo/`, not `frontend/public/`.
The React/TypeScript UI uses Tailwind CSS v4 through the Vite plugin. Utility classes live alongside JSX in
`frontend/src/components` and `frontend/src/App.tsx`; shared presentation is extracted into components there.
`frontend/src/styles/tailwind.css` is only the Tailwind entrypoint and font theme. Preflight is omitted to preserve
native filing/table rendering. The layout targets desktop screens (at least 1024px wide).

## Generated Data

| File | Purpose |
| --- | --- |
| `data/sec-edgar-filings/.../full-submission.txt` | Raw SEC submission pinned by the v1 manifest |
| `data/indexes/<filing_id>/<version>/all_chunks_embeddings.json` | Filing-scoped chunks and embeddings |
| `data/indexes/<filing_id>/<version>/filing.json` | Source/configuration identity and index SHA-256 |
| `data/query_log.jsonl` | Append-only query, answer, retrieval, latency, and Ollama metrics |

The preparation command removes temporary parser, cleaner and intermediate embedding files after publication.
The legacy direct module demos may still write shared `data/output_*.txt` files; those are not used for retrieval.
Chunks have no page or section metadata, so generated answers cannot provide claim-level citations.

## Tests

The automated tests isolate filesystem writes with temporary directories and mock SEC, Ollama, Groq and Cloudflare HTTP.

```bash
python3 -m pytest -q
```

The suite covers parsing, cleaning, indexing, retrieval, generation, CLI wiring and evaluation.
It does not replace a live SEC download or Ollama end-to-end check.

GitHub Actions runs on pull requests and pushes to `main`. It runs these Python tests and validates the committed
dev snapshot, typechecks and builds the frontend while checking that the dev snapshot is not a public asset,
and builds the API and web Docker images. These checks need no `.env`, SEC credentials, or running Ollama; they do not
replace a live filing preparation and chat smoke test.

## Performance Benchmarks

The ETL timing benchmark needs the saved NVIDIA 2026 filing and a running Ollama server:

```bash
python3 perf/benchmark_etl.py
```

The batch-size benchmark also requires the `ollama` CLI, `nvidia-smi`, and an NVIDIA GPU:

```bash
python3 perf/benchmark_batch_sizes.py
```

Historical machine-specific measurements are in [`perf/results.md`](perf/results.md).

## Project Structure

```text
ask.py                         Question CLI
api/                           FastAPI filing discovery, chat, readiness and runbook
etl_pipeline/
  ingest.py / filings.py       SEC EDGAR download and verified filing identities
  parser.py / cleaner.py       Submission extraction, HTML/table cleanup
  chunker.py / vector_store.py Local semantic chunks, Ollama embeddings, cosine retrieval
  cloud_tokens.py / cloud_chunker.py  Pinned BGE tokenizer, token-bounded cloud chunking
  cloud_embeddings.py / groq.py       Cloudflare embeddings, Groq generation (bounded, no auto-retry)
  cloud_identity.py / snapshot_provenance.py  Embedding identity and source bindings
  cloud_indexing.py            Offline preparation into the operator cache
  snapshot_export.py / snapshot_format.py / runtime_snapshot.py  Checksummed export and read-only reader
  snapshot_query.py            Shared retrieval+generation deadline for API/CLI/eval
  rag_engine.py                Prompts and provider dispatch
eval/                          Corpus manifest, dev/test questions, runners, rubric, frozen behavior contract
scripts/smoke_candidate.py     Pre-promotion smoke for staged Vercel candidates
deploy/indexes/                Frozen six-filing cloud export with manifest (tracked)
frontend/src/                  Chat-only React/Vite UI (no tests by project decision)
tests/                         Unit and integration-style tests with mocks and real tempfiles
```

## Known Limitations

- The direct module demos target NVIDIA; `ask.py` accepts only the verified dev filings.
- Local chunk limits use characters rather than model tokens (cloud chunking is token-bounded).
- Indexing embeds paragraph pieces and final chunks, which repeats embedding work.
- Retrieval reads the complete store for every query and performs a linear scan in Python.
- Retrieved chunks have no source metadata, so generated answers cannot provide citations.
- Ollama requests have configurable timeouts, but no retry or streaming support.
- The generation prompt does not enforce a context token budget.
- Generated answers can misstate numerical units even when evidence is retrieved correctly.

## Challenges, open problems, room to grow

Solved during this project (see the commit history for evidence):

- Same dimension count is not the same embedding space: Nomic/768 vs BGE/384 indexes are strictly separated and
  the reader refuses mismatched identity, not just mismatched size.
- Cloud token budgets are real budgets: a pinned, checksummed tokenizer counts every input including special
  tokens and the query prefix; the provisional 480-byte guard was replaced, not patched.
- Groq occasionally returns empty content with `finish_reason: stop`; batch evaluation fails loudly instead of
  scoring blanks, and one flaky question was diagnosed by direct payload inspection.
- Vercel's multi-service detection fought the single-origin design twice (missing `version` for `uv lock`,
  missing runtime dependencies); both were fixed from build logs, not guesses.

Open for future work (good first issues for a new dev):

- [ ] Per-user/IP rate limiting (currently per-instance semaphore + fail-closed quotas only)
- [ ] Claim-level citations with page/section anchors from the cleaned 10-K
- [ ] Streaming answers and cancellable generation in the UI
- [ ] Cold-start breakdown on Vercel (tokenizer load vs index load vs first provider call)
- [ ] Multilingual retrieval quality (Romanian): compare BGE-M3 on dev only, per the plan's gate
