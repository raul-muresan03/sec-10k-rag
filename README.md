# SEC RAG Tool

A local SEC 10-K RAG pipeline with a live FastAPI endpoint. It verifies manifest-listed filings, persists separate
indexes per filing, retrieves relevant chunks with cosine similarity, and generates answers through Ollama. The
frontend asks live filing-scoped questions by default and keeps the saved evaluation replay in an Evaluation view.

The backend uses local files without a vector database or orchestration framework.

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
- Answer filing-scoped questions through the [live API](api/README.md) or the default Chat view
- Inspect saved dev answers, evidence, and retrieval metrics in the frontend Evaluation replay
- Prepare the six dev filings with `python3 -m etl_pipeline.filing_store` or prepare one through `ask.py`
- Log questions, answers, retrieved chunks, latency, and Ollama metrics as JSONL
- Run the frontend, API and Ollama together with Docker Compose; prepare a dev filing from the Chat view

Not implemented:

- Source citations or filing metadata in answers
- Confidence scores or similarity thresholds
- Cross-filing, multi-company, or year-over-year answers; each query selects one filing
- Pinecone, LangChain, cloud LLM providers, or hybrid search

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

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/) running at `http://localhost:11434`
- The manifest-listed raw filings at their recorded `data/sec-edgar-filings/` paths
- Network access and a contact email only when obtaining SEC submissions separately
- `nomic-embed-text` for indexing and retrieval
- `gemma3:1b` by default for answer generation, or another installed Ollama model selected with `--model`

## Docker Compose (simplest local start)

Install Docker with the Compose plugin. From a clone of this repository:

```bash
docker compose up
```

Open **http://localhost:8080**. Chat lists the six manifest-pinned *dev* filings even on a clean install. Select
one and press **Prepare filing** to download the exact SEC submission, verify its checksum and identity, and build
its index. The UI shows download/model/indexing progress; on CPU, the first index can take a while. Two Ollama
models (`nomic-embed-text` and `gemma3:1b`) are downloaded automatically in the background on the first start.
They require internet access and several gigabytes of disk space. You can browse the app and Evaluation while they
download. Chat becomes available for each filing as soon as its index is ready.

Before pressing **Prepare filing**, set your real SEC contact address once (do not commit `.env`):

```bash
cp .env.example .env
# Edit SEC_API_EMAIL in .env, then restart Compose if it was already running.
```

If you edit `.env` after starting, apply it with `docker compose up -d --force-recreate api`. The API only downloads
the six pinned dev filings; it rejects a mismatched SHA-256 or SEC header. The 16 test questions and their filings
are not part of this flow. Retry from the same button if a download or index build fails. Only the web port is
exposed, bound to localhost by default; the API and Ollama are internal Compose services.

Subsequent starts use the same `docker compose up` (add `-d` for background, or `--build` after code changes)
and stop with:

```bash
docker compose down
```

The `filings` and `ollama_models` named volumes persist across `down` and image rebuilds; don't use `down -v` unless
you intend to delete downloaded filings, indexes and models. Configure `WEB_PORT` in `.env` if port 8080 is taken.
`GET http://localhost:8080/api/health` checks the API process; `/api/ready` reports when both Ollama models are
available. `/api/filings` shows each filing's preparation status. To see model-pull or API errors, run
`docker compose logs models api ollama`. The saved Evaluation replay remains independent of live preparation.

Local CPU smoke on a 16-thread Ryzen 7 7435HS with 23 GiB RAM (2026-09-28): an NVDA index took about 131 seconds
once model downloads finished; a live NVDA question took 5.18 seconds and returned five passages. During indexing,
Ollama briefly used about 800% CPU (eight cores); after the query, the three running containers used about 1.9 GiB
of RAM. The one-filing data volume used 17 MiB and the two-model volume 1.1 GiB; the Ollama container image itself
occupied about 10.6 GB locally. These are observations from one machine, not a VPS sizing target.

The commands below describe the alternative native Python/Vite setup.

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

Chat is the default view; the saved evaluation replay stays under Evaluation. Each question selects one filing,
is independent, and clears on refresh. In production the same origin serves the UI and reverse-proxies `/api`.
The React/TypeScript UI uses Tailwind CSS v4 through the Vite plugin. Reusable utility sets live in
`frontend/src/ui.ts`; `frontend/src/styles/tailwind.css` keeps only the global defaults and the disclosure marker
for retrieved chunks. Tailwind's Preflight reset is intentionally omitted to preserve native filing/table rendering.

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

The automated tests isolate filesystem writes with temporary directories and mock SEC and Ollama network calls.

```bash
python3 -m pytest -q
```

The suite covers parsing, cleaning, indexing, retrieval, generation, CLI wiring and evaluation.
It does not replace a live SEC download or Ollama end-to-end check.

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
  ingest.py                    SEC EDGAR download
  filings.py                   Verified SEC filing identities
  filing_store.py              Persistent filing index catalog and preparation
  indexing.py                  Explicit-output indexing workflow
  pipeline.py                  Single-filing CLI preparation adapter
  parser.py                    SEC submission extraction
  cleaner.py                   HTML and table cleanup
  chunker.py                   Chunk creation and Ollama embeddings
  vector_store.py              Local cosine-similarity retrieval
  rag_engine.py                Ollama prompt and answer generation
perf/                          ETL and embedding-batch benchmarks
tests/                         Unit and integration-style tests with mocks
```

## Known Limitations

- The direct module demos target NVIDIA; `ask.py` accepts only the verified dev filings.
- Chunk limits use characters rather than model tokens.
- Indexing embeds paragraph pieces and final chunks, which repeats embedding work.
- Retrieval reads the complete store for every query and performs a linear scan in Python.
- Retrieved chunks have no source metadata, so generated answers cannot provide citations.
- Ollama requests have configurable timeouts, but no retry or streaming support.
- The generation prompt does not enforce a context token budget.
- Generated answers can misstate numerical units even when evidence is retrieved correctly.
