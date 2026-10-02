# Model provider profiles

## Release boundary

Local filing preparation and chat still use Ollama. Cloud preparation is an explicit offline operator command;
cloud API/CLI/dev evaluation read verified immutable snapshots, without raw SEC files, Ollama or index writes.
A cloud profile fails before model calls when the snapshot is missing or incompatible. Switching profiles never
migrates existing indexes: local Nomic vectors have 768 dimensions; cloud BGE vectors have 384. A laptop running
the **cloud profile** uses the same Cloudflare embeddings and runtime export as the future Vercel deployment.

## Configuration

API, CLI and evaluation share `etl_pipeline.model_config.ModelConfig`. Configuration performs no network requests.
Native CLI commands require exported variables; Uvicorn supports `--env-file .env`. Compose is explicitly local and
does not receive cloud credentials. Keep Python 3.12 for the deployment target; cloud deadlines need Python 3.11+.

| Setting | Local (default) | Cloud |
| --- | --- | --- |
| `RAG_RUNTIME` | `local` | Explicit `cloud` |
| Generation provider | Ollama | Groq |
| `RAG_MODEL` | `gemma3:1b`, or another installed tag | Only `openai/gpt-oss-20b` |
| Embedding provider/model | Ollama / `nomic-embed-text` | Cloudflare / `@cf/baai/bge-small-en-v1.5` |
| Index mode | Local verified filing store | Verified immutable snapshot |
| `FILING_PREPARATION_ACCESS` | `browser` or `operator` | Only `operator` (default for cloud) |
| `RAG_TOP_N` | Positive, default 5 | 1–10 |
| `RAG_MAX_CONCURRENT_GENERATIONS` | Positive, default 1 | Per-process only, not a global serverless limit |
| `OLLAMA_BASE_URL` | Default `http://localhost:11434` | Not used |
| `OLLAMA_TIMEOUT_SECONDS` | Positive, default 120; discovery uses 5 | Not used |
| `CLOUD_TIMEOUT_SECONDS` | Not used for requests | Positive and at most 30, default 30 |
| `RAG_QUERY_TIMEOUT_SECONDS` | Existing per-call Ollama behavior retained | Total query budget, positive and at most 90, default 60 |
| `RAG_SNAPSHOT_DIR` | Not used | Default `deploy/indexes` |

Cloud also requires backend-only `GROQ_API_KEY`, `CLOUDFLARE_API_TOKEN` and a 32-character hexadecimal
`CLOUDFLARE_ACCOUNT_ID`. Missing credentials, invalid profiles and unapproved generation models fail clearly.
API keys are excluded from configuration representations and upstream error bodies are never echoed to users.
Do not print credentials or commit `.env`; never set credentials in `VITE_*` variables. Configure them through a
secure backend environment. The model allowlist is **not** a billing control: the owner must keep accounts strictly
on Free, without paid fallback or automatic billing. Quotas can still make the application unavailable.

## Provider interfaces and bounds

`get_llm_response(question, chunks, model, config=...)` preserves its positional local interface. Cloud uses Groq's
HTTPS chat-completions endpoint with system instructions and retrieved evidence; it returns the final answer plus
provider usage metrics. It requests at most 512 completion tokens, excludes reasoning from the answer, rejects blank
or truncated responses, and limits returned answers to 8,192 characters. Cloud questions are at most 2,000 UTF-8 bytes;
context is at most 10 chunks and 16,000 UTF-8 bytes. Oversized input fails rather than silently removing evidence.

Cloud document embeddings use explicit `mean` pooling. The bundled, checksummed upstream BGE WordPiece tokenizer
counts at most **480 content tokens**, with truncation disabled. The complete input, including special tokens and
the query instruction, must fit 512 tokens. Batches contain 1–100 nonblank texts and at most 8,192 final input tokens.
Token-aware chunking splits initial paragraphs and checks semantic merges against the same content budget.
Runtime question embeddings add `Represent this sentence for searching relevant passages: `; documents have no prefix.
Returned vectors are stored unchanged (provider passthrough); retrieval computes stable cosine similarity.
Each vector must have exactly 384 finite numeric entries, a finite nonzero norm and the expected count/shape/pooling.
Equal dimensions alone do not establish compatibility: the reader also checks model, provider, pooling, formatting,
normalization and tokenizer identity. Direct `text_to_embedding` remains a document-format embedding primitive;
the snapshot query interface owns query formatting and cache isolation.

Cloud requests use HTTPX without a model SDK, do not follow redirects or environment HTTP proxies, and never retry
automatically. The wall-clock timeout covers connection, headers and response body; bodies are limited to 2 MiB.
The shared cloud query interface propagates one absolute `time.monotonic()` deadline through retrieval, question
embedding and generation, and checks it before/after expensive stages. API, CLI and dev evaluation all use this
interface. Cached embeddings do not bypass an expired deadline. Local Ollama retains its
existing per-call timeouts; those do not guarantee that embedding plus generation finishes within the client's
125-second budget. Do not treat the current local setup as a production cloud timeout contract.

## Errors

Provider failures share `ModelTimeout`, `ModelUnavailable`, `ModelInvalidResponse` and `ModelRateLimited`.
Existing Ollama exception names remain compatible subclasses. HTTP chat maps quota to 429 with `Retry-After`, timeout
to 504, invalid response to 502, unavailable providers to 503, and model input violations to 422. Numeric retry hints
are clamped to 1–300 seconds; missing/invalid hints default to 60. A retry hint is not a guarantee of quota recovery.
CLI failures exit with a clear error and do not append a partial query log; evaluation failures do not publish a partial
result. Missing or incompatible filing indexes remain a separate unavailable condition.

## Verification and deployment boundary

Offline Python tests cover local/cloud configuration, request payloads, output/vector validation, timeout cancellation,
shared deadlines, response size, quota hints, safe errors and refusal to reuse local indexes. They do not prove live
account access, quotas, generation quality or embedding compatibility. Internal historical evaluation snapshots remain
separate and are not cloud runtime indexes.

Before rebuilding any dev filing, validate the real endpoint, 384 dimensions, the 512-token input limit including
special tokens/prefixes, pooling, normalization and tokenizer. Rebuild into a separate directory, retain the local
indexes, and compare only the 24 dev questions. Reserve the 16 test questions for final evaluation. Runtime snapshots
must record embedding identity/configuration and reject incompatible vectors, even if their dimensions happen to match.
Do not invent an immutable model revision when the provider does not expose one.

The runtime snapshot format and reproducible operator commands are described in [CLOUD_INDEXES.md](CLOUD_INDEXES.md).
Local cloud smoke checks do not prove Vercel bundle size, routing, concurrency, quotas, promotion or rollback.

Provider references checked on 2026-10-02:
- [Groq GPT OSS 20B](https://console.groq.com/docs/model/openai/gpt-oss-20b)
- [Cloudflare BGE small](https://developers.cloudflare.com/workers-ai/models/bge-small-en-v1.5/)
- [Cloudflare input schema](https://developers.cloudflare.com/workers-ai/models/bge-small-en-v1.5/sync-input.json)
