# Reviewing saved answers

The structured baseline in `dev_baseline.v1.json` is an AI-assisted draft.
It matches the ignored local run `data/eval-runs/20260923T125212753976Z-dev.jsonl`
by run ID and SHA-256. Keep the saved run when checking its labels; rerunning
the model produces a **different** run and needs its own review file.

Summarize the baseline (the four medium-confidence verdicts remain provisional):

```sh
venv/bin/python -m eval.answer_review_cli summarize \
  --run data/eval-runs/20260923T125212753976Z-dev.jsonl \
  --reviews eval/reviews/dev_baseline.v1.json
```

For a new **full, answer-generating** run, create a blank review template in
the ignored `data/` directory. It starts with every question unreviewed:

```sh
venv/bin/python -m eval.answer_review_cli init \
  --run data/eval-runs/RUN_ID.jsonl \
  --output data/eval-runs/RUN_ID.reviews.json
```

Inspect answers and chunks, fill in verdict, dimensions, explanation, and
evidence consulted, then change the status from `unreviewed`. Do not change
`run_id` or `run_sha256`. Confirm the four flagged baseline cases yourself;
edit their verdict/dimensions if needed, and only then set `owner_confirmed`.
The format and judgments are defined in [rubric v1](../answer_rubric.v1.md).

Compare runs only after both have review files. The command checks that
shared question IDs refer to identical gold questions; it counts transitions
only where **both** answers were reviewed:

```sh
venv/bin/python -m eval.answer_review_cli compare \
  --baseline-run data/eval-runs/BASELINE.jsonl \
  --baseline-reviews eval/reviews/dev_baseline.v1.json \
  --candidate-run data/eval-runs/CANDIDATE.jsonl \
  --candidate-reviews data/eval-runs/CANDIDATE.reviews.json
```

Use the actual baseline filename in place of `BASELINE`. Retrieval-only runs
have no generated answers and cannot receive answer-review verdicts.
