# Vercel packaging and candidate releases

One Vercel project, one HTTPS origin, two services: the `web` service builds the React/Vite application from
`frontend/`; the `api` service runs FastAPI (`api.main:app`) from the repository root for `/api/*`.
`etl_pipeline` is a library imported by the backend, not a service. No service calls another service, so no
bindings exist: the browser reaches the backend on the same origin, and the backend calls only external clouds.

## Build and bundle

- The `web` service builds the frontend with Node 22 (`engines` pin in `frontend/package.json`); its output serves
  every non-API path, including the SPA fallback. Top-level rewrites list `/api/*` first so no fallback swallows it.
- The `api` service installs root `requirements.txt` (both pinned descriptors, every dependency `==`-pinned).
- `deploy/indexes/**` is bundled explicitly via per-service `includeFiles` (snapshot `9b77d199…4e00d8`,
  ~4.8 MiB compressed); `frontend/**` sources are excluded from the function bundle.
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

## Abuse and concurrency (decided by the owner 2026-10-02)

- There is **no per-user or per-IP rate limiting**: the semaphore caps concurrent generations per instance only,
  retries are manual-only, and the Free quotas fail closed (429/503) instead of billing. A burst can still exhaust
  the daily quota and silence the demo until reset.
- The owner accepts per-instance limits plus provider quotas; no external coordination is introduced.
  No global-generation claim is made.

## Candidate release checklist (owner-authorized only)

1. Owner creates the Vercel project (repo root, Python 3.12) and sets the production variables above.
2. Deploy the candidate without touching production traffic; confirm root/assets/API share one origin and no SPA
   fallback swallows `/api/*`.
3. Verify the export is not web-accessible: no index JSON/gzip under static paths, `/_src`, mounts or rewrites.
4. Smoke: health, readiness with snapshot ID, exactly six filings, prepare refused (403), one live dev chat.
5. Record the deployment ID, SHA, snapshot ID and previous production release before any promotion (stage 5).

## Controlled releases (stage 5)

Vercel auto-builds are disabled for `main` via per-service `ignoreCommand`, so Git pushes alone never publish.
Only the `Release` GitHub Actions workflow publishes, and only after every CI check passes for the exact `main` SHA:

1. `vercel deploy --prod --skip-domain` builds a staged candidate with production variables but no traffic.
2. The release is rejected if `main` moved meanwhile (stale-SHA gate); releases serialize one at a time.
3. `scripts/smoke_candidate.py` checks health, readiness with the repository snapshot ID, exactly six ready filings,
   refused preparation, export privacy and one live dev chat. No secrets appear in its output.
4. Only the exact smoked artifact is promoted with `vercel promote`; the SHA, candidate URL and snapshot ID are
   recorded in the job summary along with the previous production release.

A green-CI failure never reaches the domain; if smoke fails, production is untouched because nothing was promoted.
For the first launch there is no previous release; the same flow promotes the first staged candidate.

### Secrets and recovery

Required repository secrets: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`; optional `VERCEL_BYPASS_TOKEN`
for candidates behind deployment protection. Promotion passes `--scope` with the team slug (overridable via
`VERCEL_SCOPE`) because the CLI cannot resolve the team from the token alone. In the project dashboard, under
Production branch tracking, **auto-assignment of production domains must be off**; otherwise staged candidates
receive traffic before promotion and the pipeline's core guarantee is void. Test the gates safely with a manual
`Release` dispatch (`promote: false`): it stages and smokes without promoting. Roll back via the `Rollback` dispatch with a previous
production deployment URL from the dashboard Deployments list; the target is smoked (without chat, to save quota)
before promotion. A rollback cannot fix an exhausted provider quota or a down provider.
