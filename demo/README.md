# Internal evaluation replay data

`demo/snapshot.v1.json` is a committed, static snapshot of **eight selected
dev examples**, kept outside the frontend and not served to users. It includes saved answers and their
original ranked top-five context without truncation, gold reference answers
and quoted reference evidence, SEC submission URLs, and run-bound AI-assisted
answer reviews. A SEC URL points to the submission, **not** to an exact
sentence or page in that submission. The original context has no claim-level
citations. Long chunks can contain irrelevant text; the reference evidence is
kept separate from retrieved context when it was not found.
No-answer labels carry their original verification note; a context-limited
refusal does not prove an exhaustive absence from the SEC submission.

The answers come from the historical full run
`20260923T125212753976Z-dev` (top 5, `gemma3:1b`). Strict hit@5/10,
multi-hop all-evidence@5/10 and MRR@10 come from the **separate**
retrieval-only run `20260925T090403491346Z-dev-retrieval` (top 10,
`nomic-embed-text`). Strict matching is a retrieval proxy, not answer
correctness. The full-run 11 pass / 6 partial / 7 incorrect review is
AI-assisted and provisional: four Adobe/Pfizer judgments still need owner
confirmation. The old full-run abstention figure is intentionally not copied
into this snapshot: its summary predates a scoring correction.

## Regenerate locally

From the repository root, with the project virtual environment and the
Git-ignored saved runs present under `data/eval-runs/`:

```sh
venv/bin/python -m scripts.export_demo
venv/bin/python -m scripts.export_demo --check
venv/bin/python -m pytest -q tests/test_demo_export.py
```

The selection and expected JSONL SHA-256s are pinned in
`demo/selection.v1.json`. To publish another reviewed run, first inspect its
answers, create a review bound to its ID and SHA-256, then update the exporter
inputs/selection and regenerate. Do not transfer verdicts to a different run.
The exporter fails on mismatched hashes, gold IDs/fields, run split, retrieval
scores, provenance and review binding. It never invokes SEC, Ollama, embedding
or generation. Only dev IDs can be selected; the held-out test questions are
not included. Run `--check` in CI: it validates the committed JSON against
tracked gold, manifest and reviews **without** the ignored local runs.

The snapshot is refreshed only after a local export and a merge to `main`;
a code change to the RAG pipeline does not automatically produce new answers.
