# Vercel packaging and candidate releases

Single Vercel project, repository root, one HTTPS origin: static React/Vite output from `public/` on the CDN,
FastAPI (`api.main:app`, pinned in `pyproject.toml`) as one Fluid-compute function for everything else.

## Build and bundle

- `vercel.json` builds the frontend with Node 22 (`engines` pin in `frontend/package.json`) and copies only
  `frontend/dist/` into `public/`. The function code never mounts or serves `public/`.
- Root `requirements.txt` includes both pinned descriptors; every runtime dependency is `==`-pinned.
- `deploy/indexes/**` is bundled explicitly via `includeFiles` (snapshot `9b77d199…4e00d8`, ~4.8 MiB compressed).
- `.vercelignore` excludes `data/`, `resurse/`, `demo/`, `tests/`, `scripts/`, `perf/`, virtualenvs and Docker files.
- Measured 2026-10-02 (clean `pip install --target` plus code, indexes and manifest): **~88 MB total**,
  far below the 500 MB Python bundle limit. Dependencies dominate (~72 MB); code, indexes and tokenizer are ~16 MB.
- Clean-container memory with all six filings loaded: ~111 MiB peak RSS, well below the 2 GB Hobby limit.

## Runtime configuration (names only; values live in the platform, never in chat, logs or commits)

| Variable | Production value |
| --- | --- |
| `RAG_RUNTIME` | `cloud` |
| `RAG_MODEL` | `openai/gpt-oss-20b` |
| `FILING_PREPARATION_ACCESS` | `operator` |
| `RAG_SNAPSHOT_DIR` | default `deploy/indexes` |
| `RAG_QUERY_TIMEOUT_SECONDS` | default `60` |
| `GROQ_API_KEY`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | backend-only secrets |

## Timeouts and limits

- Function `maxDuration` is **120 s**: headroom above the 60 s shared query budget plus ~4.3 s cold snapshot load.
  Hobby allows up to 300 s, so no extended-duration beta is needed.
- The browser aborts at 125 s; Vercel body limits are 4.5 MB per request/response (chat payloads are kilobytes).
- `/api/health` checks the process; `/api/ready` checks the export and configuration without model calls.
- Each answer logs one line: filing, model, snapshot ID, stage latencies and request ID. No secrets, questions, chunks
  or answers are logged.

## Abuse and concurrency (explicitly undecided)

- There is **no per-user or per-IP rate limiting**: the semaphore caps concurrent generations per instance only,
  retries are manual-only, and the Free quotas fail closed (429/503) instead of billing. A burst can still exhaust
  the daily quota and silence the demo until reset.
- The owner must still decide: accept per-instance limits plus provider quotas, or approve external coordination.
  Until then, no global-generation claim is made.

## Candidate release checklist (owner-authorized only)

1. Owner creates the Vercel project (repo root, Python 3.12) and sets the production variables above.
2. Deploy the candidate without touching production traffic; confirm root/assets/API share one origin and no SPA
   fallback swallows `/api/*`.
3. Verify the export is not web-accessible: no index JSON/gzip under static paths, `/_src`, mounts or rewrites.
4. Smoke: health, readiness with snapshot ID, exactly six filings, prepare refused (403), one live dev chat.
5. Record the deployment ID, SHA, snapshot ID and previous production release before any promotion (stage 5).
