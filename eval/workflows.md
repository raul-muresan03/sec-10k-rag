# Evaluation workflows

Run commands from the repository root with the project's `venv` and the
manifest-listed SEC submissions downloaded at their recorded `data/` paths.
The evaluator checks each selected filing's accession, form, filing year,
split, and SHA-256 before rebuilding a temporary per-filing index. Embeddings
require local Ollama; full runs also require the generation model. The persistent
application indexes are not reused: each run builds its own temporary indexes
and passes their paths explicitly to retrieval. `--split dev` is the default. Leave the
16 real `test` questions for the final check after dev-based changes are chosen.

## Run and inspect

```sh
# Pilot first; full mode uses five context chunks and generates answers.
venv/bin/python -m eval.run_eval --split dev --limit 4
venv/bin/python -m eval.run_eval --split dev

# Dense retrieval once at top 10 per question; no answer generation.
venv/bin/python -m eval.run_eval --split dev --mode retrieval-only
```

For every run ID `RUN_ID`, the ignored `data/eval-runs/RUN_ID.jsonl` has one
record per selected question. `RUN_ID.summary.json` stores mode, split, limit,
models, question/manifest hashes, each filing's accession/source/index hashes,
and automatic metrics. Full records include `generated_answer`, `abstained`,
retrieval/generation wall-clock seconds and Ollama counters; retrieval-only
records have ranked gold-passage matches instead of answers. Summaries include
per-filing index time and stage distributions. Ollama durations are in
**nanoseconds**, wall-clock durations in **seconds**; missing counters are
reported as missing, not zero. See the [experiment log](experiment_log.md)
for the scope and limitations of these timings and local resources.

## Interpret scores

- Strict hit@k means at least one quoted gold passage appears in the first k
  chunks; all-evidence@k means every multi-hop gold passage appears there.
  MRR@10 uses `1 / first matching rank`, or zero for an answerable miss.
  No-answer questions are excluded from these retrieval denominators.
- These are **text-match proxies** after case/whitespace normalization.
  Equivalent table evidence can score as a miss (see Starbucks in the
  [failure analysis](failure_analysis.md)). Inspect chunks separately.
- Automatic abstention is a full-response refusal check, not answer quality.
  Correctness/completeness/faithfulness/numeric precision require the manual
  [answer rubric](answer_rubric.v1.md) and a review file for that exact full
  run. Citation correctness is **not applicable** until claim-level citations
  exist. Retrieval-only runs have no answer-review or abstention metrics.

## Compare two run IDs

1. Open `data/eval-runs/BASELINE.summary.json` and
   `data/eval-runs/CANDIDATE.summary.json`. Compare `split`, `mode`, `limit`,
   question and manifest hashes, actual filing accessions/hashes, model tags,
   index configuration and `top_n`. Tags alone do not prove immutable model
   weights; different indexes, modes or cutoffs limit a quality comparison.
   Then compare like-named metrics **with their counts/denominators**. The
   frozen historical top-5 baseline has no retrospective hit@10 or MRR@10.
2. For a new full run, initialize an **unreviewed** file and inspect the
   saved answer and chunks for each question. Review files are bound to both
   run ID and JSONL SHA-256, so old verdicts cannot be copied to new answers:

   ```sh
   venv/bin/python -m eval.answer_review_cli init \
     --run data/eval-runs/CANDIDATE.jsonl \
     --output data/eval-runs/CANDIDATE.reviews.json
   venv/bin/python -m eval.answer_review_cli summarize \
     --run data/eval-runs/CANDIDATE.jsonl \
     --reviews data/eval-runs/CANDIDATE.reviews.json
   ```

3. Once both full runs have independently reviewed answers, compare only
   questions with identical gold fields and verdicts on **both** sides:

   ```sh
   venv/bin/python -m eval.answer_review_cli compare \
     --baseline-run data/eval-runs/20260923T125212753976Z-dev.jsonl \
     --baseline-reviews eval/reviews/dev_baseline.v1.json \
     --candidate-run data/eval-runs/CANDIDATE.jsonl \
     --candidate-reviews data/eval-runs/CANDIDATE.reviews.json
   ```

   The baseline's 11/6/7 verdicts remain **AI-assisted and provisional**
   until the four medium-confidence owner checkpoints are resolved. The old
   summary's 5/6 abstention is a scoring false negative; rescoring its saved
   responses yields 6/6. Do not report that correction as a model gain.
4. Record the run ID, artifact SHA-256, configuration, metric counts, observed
   failures, comparison limitations and keep/reject/unclear decision in the
   [experiment log](experiment_log.md). Keep the JSONL/summary and any new
   review file local under ignored `data/`; track only selected reports.
