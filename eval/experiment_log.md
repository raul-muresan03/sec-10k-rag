# Evaluation experiment log

Record one entry per intentional run. Saved JSONL/summary files under `data/eval-runs/`
are local and Git-ignored; the run ID and JSONL SHA-256 identify the observed
artifact. Compare **like with like**: split, question/corpus hashes, mode,
embedding and generation model tags, retrieval settings, and review coverage.
A larger `top_n` is a different measurement, not a model improvement. Tag-only
model identities do not guarantee identical model weights across dates.

New summaries report `indexing_seconds` **per filing** and `latency_seconds`
per question. Stage summaries include count, total, mean, median (`p50`),
nearest-rank `p95`, and maximum in seconds. Indexing includes building the
temporary index, including source rechecks; preflight and artifact writing are
outside that stage. These stage totals are not a full end-to-end wall clock.
Ollama-reported token counts are in tokens; its reported durations are in
**nanoseconds**, with coverage per field. They are not added to application
wall-clock time, and missing fields are not treated as zero. Ollama embed
requests do not provide token counters here. The runtime environment records
platform, Python version, and logical CPU count, not Ollama's GPU/peak memory.
No dollar cost is inferred for local inference.

## Earlier smoke checks (excluded from cross-run comparisons)

- `20260923T124028271242Z-dev`: JSONL SHA-256
  `40008a8da1e4f15419182f5764cb0e91813f4a9697386d6ba50447bcdb9ed963`.
  Four NVIDIA dev questions, `gemma3:1b`, dense top 5, 2/3 strict hits,
  0/1 multi-hop complete, 1/1 no-answer refusal. Legacy mean times:
  index 1.570 s, retrieval 1.283 s, generation 1.553 s. The index reuse
  path was not provenance-verified; answers are not separately reviewed.
  **Decision: unclear** as a quality/speed comparison; retain as a smoke check.
- `20260925T085625836378Z-dev`: JSONL SHA-256
  `4bfb2c45ff4a30e1b50945944032699327034d5772510f1295d4a21267f5cdcd`.
  One NVIDIA narrative dev question, verified and rebuilt index,
  `gemma3:1b`, dense top 5; strict hit 1/1, generated answer unreviewed.
  Index 14.815 s, retrieval 0.140 s, generation 2.625 s. No multi-hop or
  no-answer score is defined for this subset. **Decision: unclear** for any
  quality/speed comparison; keep as a provenance pilot.

## 20260923T125212753976Z-dev — saved generation baseline

- Artifact: `data/eval-runs/20260923T125212753976Z-dev.jsonl`;
  SHA-256 `69db1f90d8e1bc7125c3eda20246f6cc56a448d8d040a73be336a8cc68eac60d`.
- Configuration: 24 dev questions / 6 filings, `gemma3:1b`, dense retrieval
  top 5, `nomic-embed-text`. Six raw filing hashes later matched the v1
  manifest; this legacy run did not capture immutable model/index identities.
- Quality: strict hit@5 **15/18**, multi-hop all-evidence@5 **4/6**. The
  original summary says abstention **5/6**; calibrated rescoring of the
  *saved answers* gives **6/6**, not a generation improvement. AI-assisted
  answer review proposes 11 pass / 6 partial / 7 incorrect, with four
  owner-confirmation cases still open.
- Timing in original summary (means only): index preparation **16.589 s**
  per filing; retrieval **0.348 s** and generation **0.663 s** per question.
  Detailed distributions, per-filing times, and Ollama token totals were
  not saved in its summary; no new timings are attributed retrospectively.
- Observed failures: wrong-year Starbucks value, numeric scope/format errors,
  incomplete comparisons, and NVIDIA/Adobe missing retrieval evidence;
  see [failure analysis](failure_analysis.md).
- Comparison/decision: reference run; **keep as a frozen baseline**, with
  answer-review totals explicitly provisional.

## 20260925T090403491346Z-dev-retrieval — retrieval baseline

- Artifact: `data/eval-runs/20260925T090403491346Z-dev-retrieval.jsonl`;
  SHA-256 `2e5e321dd1510b37d3832b226be16176ac1296b9338bbf5c3bab5d2444e697bf`.
- Configuration: 24 dev questions / 6 verified v1 filings, dense retrieval
  once at top 10, `nomic-embed-text` tag, no generation. Its ignored summary
  stores corpus/question and per-filing index hashes. This run predates the
  new timing distribution fields.
- Quality (strict proxy): hit@5 **15/18**, hit@10 **17/18**,
  MRR@10 **0.6484**; multi-hop all-evidence@5 **4/6**, @10 **5/6**.
  No answer-review verdicts or abstention scores apply to retrieval-only.
- Timing in saved summary (means only): indexing **12.287 s** per filing,
  retrieval **0.141 s** per question. No generation or Ollama generation tokens.
- Observed failure: Adobe multi-hop has neither gold passage at rank 10;
  NVIDIA multi-hop passages first appear together at rank 7. The Starbucks
  baseline's alternative table evidence remains a separate manual judgment.
- Comparison/decision: hit@5 numerically matches the old baseline; the
  extra hit@10 and multi-hop completion result from a wider ranking cutoff.
  **Keep as retrieval diagnostic**, not evidence of a system improvement.

## 20260925T092037572194Z-dev — timing-instrumented full dev run

- Artifact: `data/eval-runs/20260925T092037572194Z-dev.jsonl`;
  SHA-256 `8e63896c79b26d84f62933a7a78a49d7da12675e0cc99c61494555b70dd945de`.
- Configuration: 24 dev questions / 6 verified v1 filings, rebuilt dense
  indexes with `nomic-embed-text` tag, `gemma3:1b` generation, top 5. Source
  and index hashes are in its local summary; neither Ollama tag is immutable.
  This run started before `runtime_environment` was added, so it does **not**
  contain a hardware snapshot.
- Quality: strict hit@5 **15/18**, multi-hop all-evidence@5 **4/6**;
  automatic no-answer abstention **5/6**. Answer-review verdicts for this new
  run are **unreviewed**; the old 11/6/7 labels do not transfer to it.
- Wall-clock stage totals: index building **67.769 s** across six filings
  (mean **11.295**, p95 **20.371**); retrieval **3.321 s** across 24 questions
  (mean **0.138**, p95 **0.248**); generation **12.122 s** across 24 questions
  (mean **0.505**, p95 **1.161**). These measured stages exclude preflight
  and other overhead; they are not claimed as total job time.
- Ollama generation reports input/prompt **43,894 tokens** and output
  **746 tokens** (24/24 questions report each field). Its `total_duration`
  sums to **11,921,756,754 ns**; do not add that to generation wall time.
  Local inference has no measured dollar price in this log.
- Observed failure: `sbux-2019-no-answer` now fabricates “276.5 cups of
  coffee”, rather than refusing; this is a newly generated response, not a
  scorer correction. Other answer failures have not been manually reviewed.
- Comparison/decision: strict hit@5 remains **15/18**; the saved baseline's
  abstentions rescore to **6/6**, while this run is **5/6**. Tag-only model
  identity and sampling do not establish a causal regression. **Unclear**
  until answers are reviewed; retain this run as a timing snapshot.

## 20260925T092321637476Z-dev — one-question instrumentation pilot

- Artifact: `data/eval-runs/20260925T092321637476Z-dev.jsonl`;
  SHA-256 `bd5273fb0a0ead20a30f561ab099832497069e62664e72c7eda58052c0385bb4`.
- Configuration: NVIDIA 2026 narrative dev question only, top 5, same dense
  indexer tags and `gemma3:1b` generation. Runtime snapshot: Linux x86_64,
  Python 3.12.3, 16 logical CPUs (not a GPU/RAM measurement).
- Quality: strict hit@5 **1/1**; generated answer **unreviewed**. No
  multi-hop or no-answer denominator exists for this one-question pilot.
- Wall-clock stages: NVIDIA index **10.423 s**, retrieval **0.137 s**,
  generation **0.572 s**. Ollama reports **1,299 prompt tokens** and **76
  output tokens**; its total duration is **565,580,154 ns** (1/1 reporting).
  With one observation, p50/p95 are the same value and have no tail meaning.
- Observed failures: no answer verdict assigned; only instrumentation checked.
- Comparison/decision: sample and workload too small for a quality or speed
  comparison. **Keep** as a field-format check, not as an optimization result.

## Next entry template

- Run ID / JSONL SHA-256; split, question/corpus hashes and mode.
- Configuration: models (tag/digest status), index/chunking, top N, hardware
  and review coverage.
- Quality: strict retrieval proxy and, separately, reviewed answer verdicts.
- Timing/resources: per-stage totals/distributions, Ollama tokens/durations
  with coverage; no invented local-dollar cost.
- Representative failures and comparison with the **same** baseline/setting.
- Decision: **keep**, **reject**, or **unclear**, with the reason.
