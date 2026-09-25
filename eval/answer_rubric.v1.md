# Answer review rubric v1

Version: `answer-review-v1`. Review the **generated answer for a particular
saved run**, the question and reference, and the retrieved text. The gold answer
may be paraphrased; a strict `evidence_found` match is neither required nor
sufficient for correctness. Consult the filing if a table, quote, or absence
claim cannot be settled from the retrieved chunks. Record uncertainty; do not
turn a missing quote into a proven parser or retrieval failure.

## Overall verdict

- `pass`: all required facets are answered with source-supported claims;
  equivalent wording and numerically equivalent units are acceptable.
- `partial`: a useful core answer, but a required facet or requested precision
  is missing, or wording is more specific than the available evidence.
- `incorrect`: a wrong fact, entity, value, comparison, period, or scope.
  A plausible-sounding answer does not outweigh a material error.

For a gold `no_answer`, a complete context-limited refusal with no unsupported
claim is a pass. A fabricated answer or failure to refuse is incorrect. A false
refusal to an answerable question is incorrect. The gold no-answer labels are
owner-reviewed, but this review does not prove absence through a new exhaustive
search of the filing.

## Dimensions

Each dimension is a **manual judgment**, not a formula for the overall verdict:

- `completeness`: `pass` for all required facets; `partial` for a useful core
  missing a facet; `fail` for wrong scope or no usable answer. A valid no-answer
  refusal is `not_applicable` here.
- `faithfulness`: `pass` for claims supported by inspected context; `partial`
  for wording exceeding evidence without overturning the core; `fail` for a
  material unsupported or contradicted claim. With no factual claim, use
  `not_assessed`.
- `numeric_precision`: `pass` for the correct quantity, period, unit,
  calculation, and requested precision; `partial` for a useful magnitude but
  missing precision or comparison; `fail` for a wrong metric, year, value, or
  calculation. Use `not_applicable` if no numeric facet is requested.
- `abstention`: `pass` for correctly refusing no-answer or not falsely refusing
  answerable; `fail` for a fabricated no-answer response or false refusal.
  Use `not_assessed` if refusal cannot be judged.
- `citations`: always `not_applicable` in v1; the system has no claim-level
  citations yet.

`not_assessed` means insufficient review, **not** success; use it when no claim
exists or a dimension cannot be established. For example, the saved Starbucks
table contains the 2019 number even though the quoted passage fails a strict
text match; the generated 2018 number remains incorrect. A multi-hop answer
must cover both sides and the requested relationship. For Pfizer, “sale” is
more specific than the retrieved “full disposition”; this rubric marks it
partial pending owner confirmation.

## Review record and publication rules

- A review file is bound to one `run_id` and the SHA-256 of its **entire JSONL
  run** (answers and retrieved chunks). Each `question_id` within the file is
  the other half of the review key. Do not copy labels into another run.
- `unreviewed` has no verdict. `ai_reviewed` records an AI-assisted assessment;
  `needs_owner_confirmation` is an AI proposal requiring owner judgment;
  `owner_confirmed` records an explicit owner decision. `confidence` records
  uncertainty independently of the verdict.
- Record an explanation and the evidence consulted, such as `retrieved:R2`,
  `gold:questions.jsonl`, or an inspected cleaned filing. An unsupported label
  should not be saved as reviewed.
- Aggregate verdicts over **reviewed records only** and report unreviewed and
  pending-owner counts separately. While either is nonzero, the verdict totals
  are provisional. Even after owner checkpoints, the remaining AI-assisted
  labels are not independently human-validated gold.

The [dev baseline proposals](reviews/dev_baseline.v1.json) correspond to the
[AI-assisted failure analysis](failure_analysis.md). The four medium-confidence
cases requiring owner confirmation are `adbe-2018-narrative`,
`adbe-2018-multi-hop`, `pfe-2015-narrative`, and `pfe-2015-multi-hop`.
