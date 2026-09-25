# Evaluation Corpus v1

This directory defines the source material for the first evaluation set.
Each filing is selected by ticker and SEC filing year, not fiscal year. The
current ingestion downloads the newest non-amended `10-K` filed in that year.
The [v1 corpus manifest](corpus_manifest.v1.json) records the exact submissions
used to create the evaluation set.

## Selection Rules

- Include exactly 10 filings from 10 companies and several industries.
- Use Form `10-K` only; exclude amendments such as `10-K/A`.
- Cover legacy, transitional, and modern filing layouts.
- Prefer filings that can support narrative, numeric, and multi-hop questions.
- Keep all questions for a company in its assigned split.

For this corpus, legacy means filed through 2015, transitional means filed
from 2016 through 2020, and modern means filed from 2021 onward. These are
time-based selection buckets, not parser-quality claims. The later manual
audit will record the actual structure and any parser data loss.

## Dev Filings (6)

### NVIDIA CORP (NVDA)

- Filing: `NVDA`, filing year 2026; industry: semiconductors; layout: modern.
- Rationale: recent Inline XBRL filing with extensive risk disclosures and financial tables.

### AMAZON COM INC (AMZN)

- Filing: `AMZN`, filing year 2021; industry: retail and cloud services; layout: modern.
- Rationale: adds distinct business segments and cross-section relationships.

### STARBUCKS CORP (SBUX)

- Filing: `SBUX`, filing year 2019; industry: restaurants; layout: transitional.
- Rationale: adds an off-calendar fiscal year and store and segment disclosures.

### ADOBE SYSTEMS INCORPORATED (ADBE)

- Filing: `ADBE`, filing year 2018; industry: software; layout: transitional.
- Rationale: adds a transition-era filing with subscription and digital-media reporting.

### PFIZER INC (PFE)

- Filing: `PFE`, filing year 2015; industry: pharmaceuticals; layout: legacy.
- Rationale: adds legacy pharmaceutical disclosures about products, patents, and regulation.

### FORD MOTOR CO (F)

- Filing: `F`, filing year 2014; industry: automotive; layout: legacy.
- Rationale: adds a legacy industrial filing with automotive, credit, and pension data.

## Test Filings (4)

### Apple Inc. (AAPL)

- Filing: `AAPL`, filing year 2024; industry: consumer technology; layout: modern.
- Rationale: adds product and geographic reporting in a recent large-company filing.

### JPMORGAN CHASE & CO (JPM)

- Filing: `JPM`, filing year 2023; industry: financial services; layout: modern.
- Rationale: adds a regulated financial company with dense tables and linked disclosures.

### CHEVRON CORP (CVX)

- Filing: `CVX`, filing year 2019; industry: energy; layout: transitional.
- Rationale: adds an asset-heavy company with commodity, reserves, and segment disclosures.

### Walmart Inc. (WMT)

- Filing: `WMT`, filing year 2014; industry: retail; layout: legacy.
- Rationale: adds a legacy retail filing with an off-calendar year and segment disclosures.

## Evaluation Target

The [evaluation questions](questions.jsonl) contain 40 records,
four per filing (24 dev, 16 test):

| Question type | Target |
| --- | ---: |
| Narrative | 10 |
| Numeric | 10 |
| Multi-hop | 10 |
| No-answer | 10 |
| **Total** | **40** |

Each filing has one question of each type. The questions and answers were
drafted with AI assistance; their quoted evidence was matched to both the
selected SEC document and cleaned text. The project owner has reviewed the
answers, including numeric values and no-answer labels. Use dev to improve
the application; reserve test for the final check rather than tuning against it.

## Verification

Each selected ticker/year was downloaded through the current ingestion code,
and its SEC submission header confirms form `10-K` and the filing year.
See [the inspection notes](inspection.md) for parser and cleaner findings.

## Corpus manifest

`corpus_manifest.v1.json` identifies the ten submissions behind `questions.jsonl`.
Each entry records the ticker, SEC filing year, split, accession, repository-relative
file path, SEC URL, and SHA-256 of the downloaded `full-submission.txt` bytes.
The files under `data/` are local and are not committed. To verify one after
downloading it, run `sha256sum` on its `path` and compare with its `sha256`.

The manifest has version `1`. The runner still selects by ticker and year; it
does not check the accession or hash automatically. Verify them before comparing
runs made from separately downloaded filings.

## Running the evaluator

Run a four-question dev pilot (the first four dev questions are NVIDIA):

```sh
venv/bin/python -m eval.run_eval --split dev --limit 4
```

After inspecting the pilot output, run the full dev split:

```sh
venv/bin/python -m eval.run_eval --split dev
```

The runner indexes each ticker/year once per run, then records retrieved chunks,
generated answers, evidence matches, retrieval/generation latency, and Ollama
timing counters. It writes a JSONL record per question and a JSON summary under
`data/eval-runs/`. The summary reports indexing time separately from per-query
retrieval and generation time. Override the defaults with `--top-n`, `--model`,
`--questions`, and `--limit`. Use `--split test` only for a final check after
dev-based tuning.

Evidence hits require the quoted passage to appear in a retrieved chunk after
case and whitespace normalization; this is a strict text-match proxy, not a
semantic relevance or answer-correctness score. For example, the Starbucks
2019 numeric dev result retrieves a table with 2019 Americas operating income
of $3,782.8 million, but its quoted evidence does not match exactly. The model
answered $3,485.2 (the 2018 column value), so that answer is still incorrect.
Review such table and multi-hop cases manually before interpreting hit rates.

Automatic abstention scoring recognizes the complete response "Information not
available in the provided context" or "Information not found in the provided
context" (ignoring case, whitespace, and trailing periods/exclamation marks).
Other refusal wording requires manual review. The saved results and summary
reflect the scoring rules at the time of that run; changing the evaluator does
not update earlier JSONL files or summaries.

Rescoring the saved dev baseline `20260923T125212753976Z-dev.jsonl` recognizes
6/6 no-answer abstentions instead of the original 5/6, with 0/18 false
abstentions. Strict evidence hit@5 remains 15/18. The ignored baseline files
have not been rewritten.

See [the dev baseline failure analysis](failure_analysis.md) for per-question
verdicts, failure causes, supporting retrieval ranks, and the next changes to test.
