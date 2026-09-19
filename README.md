# SEC RAG Tool

A local command-line prototype for asking questions about an SEC 10-K filing. The project downloads a filing from SEC EDGAR, extracts and cleans its HTML, creates embeddings with Ollama, stores them in a local JSON file, retrieves relevant chunks with cosine similarity, and sends that context to a local Ollama generation model.

This repository is intentionally small and dependency-light. It does not use a vector database, an orchestration framework, a web API, or a frontend.

## Current Scope

Implemented:

- Download the latest 10-K for a ticker with `sec-edgar-downloader`
- Extract a document block from an SEC submission
- Remove hidden and noisy HTML and convert tables to Markdown-like text
- Build semantic chunks from adjacent paragraphs
- Generate embeddings in batches with Ollama's `nomic-embed-text` model
- Store chunks and embeddings locally in JSON
- Retrieve chunks with brute-force cosine similarity
- Generate an answer with a local Ollama model
- Run download, indexing, retrieval, and generation from `ask.py`

Not implemented:

- Source citations or filing metadata in answers
- Confidence scores or similarity thresholds
- Multi-filing, multi-company, or year-over-year retrieval
- Pinecone, LangChain, cloud LLM providers, or hybrid search
- FastAPI, Streamlit, Docker, or a web interface

## How It Works

```text
SEC EDGAR submission
        |
        v
parse document block
        |
        v
clean HTML and tables
        |
        v
split and merge adjacent paragraphs
        |
        v
embed chunks with Ollama
        |
        v
data/all_chunks_embeddings.json
        |
        v
embed question -> cosine similarity -> top N chunks
        |
        v
Ollama generation -> terminal answer
```

The local vector store contains only chunk text and embedding vectors. Each query reloads the JSON file and compares the query embedding with every stored vector.

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/) running at `http://localhost:11434`
- Network access and an email address for SEC EDGAR downloads
- `nomic-embed-text` for indexing and retrieval
- `gemma3:1b` by default for answer generation, or another installed Ollama model selected with `--model`

## Setup

Run all commands from the repository root.

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r etl_pipeline/requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Set the SEC EDGAR contact email in `.env`:

```ini
SEC_API_EMAIL=your_email@example.com
```

Install and start Ollama, then pull the models used by the application:

```bash
ollama pull nomic-embed-text
ollama pull gemma3:1b
```

## Build the Local Index

`ask.py` prepares the index automatically. It checks SEC for the requested ticker, downloads the matching 10-K,
runs the ETL pipeline, and records the active accession in `data/active_accession.txt`. A matching index is reused;
changing the filing rebuilds the single active index.

`--year` is required and means the SEC filing year, not the fiscal year. Supported years run from 1994 through the
current year. Amendments such as `10-K/A` are excluded.

Downloaded submissions remain available at:

```text
data/sec-edgar-filings/<TICKER>/10-K/<ACCESSION>/full-submission.txt
```

The embedding request batch size defaults to `512`. Override it through the process environment when needed:

```bash
EMBEDDING_BATCH_SIZE=128 python3 ask.py --ticker NVDA --year 2026 "Who is the CEO?"
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

The CLI prints ETL progress when rebuilding, the vector-store path, retrieval time, generation time, and final
answer. The default values are `--top-n 5` and `--model gemma3:1b`.

## Generated Data

| File | Purpose |
| --- | --- |
| `data/sec-edgar-filings/.../full-submission.txt` | Raw SEC submission downloaded from EDGAR |
| `data/output_parser.txt` | Extracted `<DOCUMENT>` block whose type is exactly `10-K` |
| `data/output_cleaner.txt` | Cleaned filing text and Markdown-like tables |
| `data/all_embeddings.json` | Intermediate paragraph embeddings |
| `data/all_chunks_embeddings.json` | Final chunk text and embeddings used for retrieval |
| `data/active_accession.txt` | SEC accession identifying the active index |
| `data/all_chunks.txt` | Human-readable chunk dump produced by the chunker module command |

The parser, cleaner, and chunker outputs are overwritten by later runs. Downloaded SEC submissions remain in their
ticker and accession directories. The sidecar identifies the active filing, but chunks still have no page or section
metadata, so the store remains an index for one processed filing at a time.

## Tests

The automated tests isolate filesystem writes with temporary directories and mock SEC and Ollama network calls.

```bash
python3 -m pytest -q
```

The suite covers ingestion configuration, parsing, cleaning, chunking, retrieval, generation, CLI wiring, and imports from the repository root. It does not replace a live SEC download or Ollama end-to-end check.

## Performance Benchmarks

The ETL timing benchmark expects NVIDIA accession `0001045810-26-000021` at the path hard-coded in `perf/benchmark_etl.py` and requires a running Ollama server:

```bash
python3 perf/benchmark_etl.py
```

The batch-size benchmark also requires the `ollama` CLI, `nvidia-smi`, and an NVIDIA GPU:

```bash
python3 perf/benchmark_batch_sizes.py
```

Historical measurements and their hardware context are recorded in [`perf/results.md`](perf/results.md). They are machine-specific and should not be treated as general performance guarantees.

## Project Structure

```text
ask.py                         Question CLI
etl_pipeline/
  ingest.py                    SEC EDGAR download
  pipeline.py                  Active-index cache and ETL orchestration
  parser.py                    SEC submission extraction
  cleaner.py                   HTML and table cleanup
  chunker.py                   Chunk creation and Ollama embeddings
  vector_store.py              Local cosine-similarity retrieval
  rag_engine.py                Ollama prompt and answer generation
perf/                          ETL and embedding-batch benchmarks
tests/                         Unit and integration-style tests with mocks
```

## Known Limitations

- The direct module demos are configured around NVIDIA, while `ask.py` accepts any supported ticker.
- Chunk limits use characters rather than model tokens.
- Indexing embeds paragraph pieces and final chunks, which repeats embedding work.
- Retrieval reads the complete store for every query and performs a linear scan in Python.
- Retrieved chunks have no source metadata, so generated answers cannot provide citations.
- Ollama requests have no timeout, retry, or streaming support.
- The generation prompt does not enforce a context token budget.
- Processed outputs and the local vector store use shared filenames and are overwritten by the next filing.
