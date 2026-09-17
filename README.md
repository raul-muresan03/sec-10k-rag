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
- Run the retrieval and generation flow from `ask.py`

Not implemented:

- Source citations or filing metadata in answers
- Confidence scores or similarity thresholds
- Multi-filing, multi-company, or year-over-year retrieval
- Pinecone, LangChain, cloud LLM providers, or hybrid search
- FastAPI, Streamlit, Docker, or a web interface
- A single command that orchestrates the complete ingestion pipeline

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

The ETL stages currently run separately and write fixed filenames under `data/`. A fresh clone does not contain a vector store because `data/` is gitignored.

### 1. Download a filing

The built-in module command downloads the latest NVIDIA 10-K:

```bash
python3 -m etl_pipeline.ingest
```

To download the latest 10-K for another ticker:

```bash
python3 -c "from etl_pipeline.ingest import download_10k; download_10k('AAPL')"
```

Downloaded submissions are stored at:

```text
data/sec-edgar-filings/<TICKER>/10-K/<ACCESSION>/full-submission.txt
```

### 2. Parse the downloaded submission

Pass the actual ticker and accession directory created by the downloader:

```bash
python3 -c "from etl_pipeline.parser import parse_10K; parse_10K('data/sec-edgar-filings/<TICKER>/10-K/<ACCESSION>/full-submission.txt')"
```

This writes `data/output_parser.txt`.

The shortcut below is only valid for the NVIDIA accession currently hard-coded in `etl_pipeline/parser.py`:

```bash
python3 -m etl_pipeline.parser
```

### 3. Clean the filing

```bash
python3 -m etl_pipeline.cleaner
```

This reads `data/output_parser.txt` and writes `data/output_cleaner.txt`.

### 4. Create chunks and embeddings

Make sure Ollama is running and `nomic-embed-text` is installed, then run:

```bash
python3 -m etl_pipeline.chunker
```

This creates `data/all_chunks_embeddings.json`, the local vector store required by the question CLI.

The embedding request batch size defaults to `512`. Override it through the process environment when needed:

```bash
EMBEDDING_BATCH_SIZE=128 python3 -m etl_pipeline.chunker
```

## Ask Questions

With the local index built and Ollama running:

```bash
python3 ask.py "Who is the CEO of NVIDIA?"
```

Select the number of retrieved chunks and generation model:

```bash
python3 ask.py "What risks does the company describe?" --top-n 3 --model gemma3:1b
```

The CLI prints the vector-store path, retrieval time, generation time, and final answer. The default values are `--top-n 5` and `--model gemma3:1b`.

## Generated Data

| File | Purpose |
| --- | --- |
| `data/sec-edgar-filings/.../full-submission.txt` | Raw SEC submission downloaded from EDGAR |
| `data/output_parser.txt` | First extracted `<DOCUMENT>` block |
| `data/output_cleaner.txt` | Cleaned filing text and Markdown-like tables |
| `data/all_embeddings.json` | Intermediate paragraph embeddings |
| `data/all_chunks_embeddings.json` | Final chunk text and embeddings used for retrieval |
| `data/all_chunks.txt` | Human-readable chunk dump produced by the chunker module command |

The parser, cleaner, and chunker outputs are overwritten by later runs. Downloaded SEC submissions remain in their ticker and accession directories. The store has no ticker, year, accession, page, or section metadata, so it should be treated as an index for one processed filing at a time.

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
  parser.py                    SEC submission extraction
  cleaner.py                   HTML and table cleanup
  chunker.py                   Chunk creation and Ollama embeddings
  vector_store.py              Local cosine-similarity retrieval
  rag_engine.py                Ollama prompt and answer generation
perf/                          ETL and embedding-batch benchmarks
tests/                         Unit and integration-style tests with mocks
```

## Known Limitations

- The module entry points are configured around NVIDIA, and the parser shortcut contains a fixed accession path.
- The parser selects the first `<DOCUMENT>` block rather than checking its `<TYPE>` value.
- Chunk limits use characters rather than model tokens.
- Indexing embeds paragraph pieces and final chunks, which repeats embedding work.
- Retrieval reads the complete store for every query and performs a linear scan in Python.
- Retrieved chunks have no source metadata, so generated answers cannot provide citations.
- Ollama requests have no timeout, retry, or streaming support.
- The generation prompt does not enforce a context token budget.
- Processed outputs and the local vector store use shared filenames and are overwritten by the next filing.
