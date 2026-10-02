# Immutable cloud filing indexes

## Compatibility contract

The local Ollama/Nomic store and cloud Cloudflare/BGE store are separate. Existing local indexes are neither rewritten
nor reused. Cloud document and question vectors come from the same API/model with explicit `mean` pooling, dimension
384 and provider-returned values. A laptop validating the cloud profile and the public runtime read the same export.

The bundled tokenizer is pinned by upstream revision and SHA-256; it never downloads at runtime. Content is limited
to 480 tokens and final inputs to 512, including BERT special tokens and the query instruction. Semantic merges and
initial paragraph splits obey these limits. Each batch has at most 100 texts and 8,192 final input tokens.
Cloudflare does not expose an immutable weight/tokenizer revision. The manifest records that limitation instead of
claiming byte-identical future re-embedding. Checksums freeze the **export**, not the provider's future responses.

## Operator preparation

Use Python 3.12 and install `etl_pipeline/requirements.txt`. Export the approved cloud settings securely in the operator
shell: `RAG_RUNTIME=cloud`, `RAG_MODEL=openai/gpt-oss-20b`, and the backend-only Groq/Cloudflare credentials described
in [MODEL_PROVIDERS.md](MODEL_PROVIDERS.md). Keep accounts on Free without paid fallback. Never paste keys into chat,
logs or committed files. The local setup wizard uses the Git-ignored, permission-600 file `resurse/cloud.env`.

Raw dev submissions must match `eval/corpus_manifest.v1.json`; this command does not download from SEC. First validate
one filing in a new, ignored output directory, then build the release into a **new** `deploy/indexes` directory:

```sh
python -m etl_pipeline.cloud_indexing --ticker NVDA --year 2026 --output resurse/cloud-candidate
python -m etl_pipeline.cloud_indexing --output deploy/indexes
```

Offline cloud cache entries live under `data/cloud-indexes/`, separate from `data/indexes/`. Completed matching entries
are reused only after checksum verification; interrupted builds do not publish a partial export. Publication refuses
an existing destination. For a later snapshot, choose a new candidate directory, verify it, and deliberately replace
the single tracked active set in a dedicated data commit. Do not commit historical cache versions or raw submissions.

## Export and runtime reader

`manifest.json` contains snapshot/configuration IDs, indexing source hashes, SEC URLs, dev filing identities, source
hashes, chunk counts, compressed/expanded sizes and per-file SHA-256 checksums. Each filing is deterministic JSON/gzip
with texts and full-precision vectors. Indexing provenance excludes generation prompts/API code; changing them does
not invalidate document data. `demo/snapshot.v1.json` remains a different, historical evaluation artifact.

`SnapshotStore` verifies the manifest, all file checksums and every vector before serving queries. It rejects unknown
schemas, duplicate IDs, non-dev entries, path escapes, symlinked files, incompatible embedding identity, invalid norms
and oversized data. Limits are 128 KiB for the manifest, 32 MiB compressed/64 MiB expanded per filing and
128 MiB compressed/256 MiB expanded in total. Only one to six dev filings are accepted; a release must contain all six.
The read-only reader needs neither the corpus manifest/raw files nor Ollama and creates no directories or files.

Cloud question embeddings use a bounded 128-entry cache keyed by snapshot ID, embedding configuration ID and question.
Each independent query shares one total deadline across retrieval and both providers; expired budgets never trigger
generation. No provider retry is automatic. The semaphore remains per process, not a global serverless limit.

Native cloud usage (after exporting the secure environment):

```sh
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
python ask.py 'How does NVIDIA assign revenue geographically?' --ticker NVDA --year 2026
python -m eval.run_eval --split dev --question-interval-seconds 61
```

The evaluation interval is explicit operator pacing, outside each query deadline, not an automatic retry. It reduces
burst quota exhaustion; account limits may still differ. Evaluation uses the frozen export instead of rebuilding and
records snapshot/model/prompt provenance and actual usage. Test questions are reserved for final evaluation and are
rejected by this public dev-snapshot workflow. Evaluation output remains separate from runtime files.

The export is outside static assets. If committed to a public repository, its text is still visible in Git; "private"
means not served as a web asset. Vercel packaging, exposure checks, production publication and rollback are separate
deployment gates. Do not infer deployment readiness from a successful local cloud chat.

## Verified dev release

Snapshot `9b77d19945eb0d8000d1137d5be2ff6ffda03c8ea7e5f641ee4298039f4e00d8`, built 2026-10-02 from
code `d980353` with Cloudflare `@cf/baai/bge-small-en-v1.5` (384 dimensions, explicit `mean` pooling,
provider-passthrough vectors). All six dev filings, 2,869 chunks total:

| Filing | Chunks | Compressed | Expanded |
| --- | --- | --- | --- |
| ADBE 2018 | 547 | 931.0 KiB | 4153.9 KiB |
| AMZN 2021 | 396 | 671.3 KiB | 2987.7 KiB |
| F 2014 | 828 | 1415.4 KiB | 6287.1 KiB |
| NVDA 2026 | 453 | 786.7 KiB | 3466.5 KiB |
| PFE 2015 | 197 | 348.8 KiB | 1533.7 KiB |
| SBUX 2019 | 448 | 774.8 KiB | 3408.1 KiB |

Totals: 4.812 MiB compressed, 21.325 MiB expanded. Local Nomic indexes were neither rewritten nor reused.

Dev retrieval-only run `20261002T133927181691Z-dev-cloud` (frozen export, top-10, all 24 dev questions, no test
questions used): hit@10 15/18 (0.833), multi-hop complete evidence 6/6, MRR@10 0.520, mean retrieval 0.256 s.
Three evidences missed the top 10: `nvda-2026-narrative`, `sbux-2019-numeric`, `f-2014-narrative`.
Live NVIDIA cloud chat returned HTTP 200 in about 0.655 s with Ollama requests forbidden.

Clean API-container sizing (non-root, read-only, network disabled, providers excluded): cold reader 4.292 s,
peak RSS 110.97 MiB, synthetic per-filing retrieval CPU 0.021–0.088 s. These are not Vercel measurements.
The 24-question full generation run is deferred to final evaluation to preserve Free quotas for deploy smoke tests.
