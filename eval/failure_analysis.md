# Dev baseline failure analysis

## Scope and review rules

- Run: `data/eval-runs/20260923T125212753976Z-dev.jsonl` (local, Git-ignored).
- Run SHA-256: `69db1f90d8e1bc7125c3eda20246f6cc56a448d8d040a73be336a8cc68eac60d`.
- Configuration: `gemma3:1b`, `top_n=5`, 24 dev questions, six filings from the
  [v1 manifest](corpus_manifest.v1.json). No new generation or test-split evaluation was performed.
- This is an AI-assisted review of saved answers against the owner-validated
  [questions](questions.jsonl) and retrieved text, not an independently human-validated answer score.
- **Pass:** answers the required facets with source-supported claims. Paraphrases are accepted.
  **Partial:** a useful core answer, but a required facet/precision is missing or wording exceeds the evidence.
  **Incorrect:** wrong fact, entity, comparison, or scope. Partial and incorrect both require follow-up.
- Completeness includes the reference's device coverage for Adobe and research coverage for Pfizer.
  These are rubric-dependent judgments, marked medium confidence. The no-answer gold labels are reused;
  this review checks the refusals, not a new exhaustive search proving absence from each submission.
- `R1` through `R5` mean the saved retrieval ranks for that question. A passage in another question's
  retrieved chunks is evidence it was indexable in that same run; exact-match misses alone are not failures.
- Primary labels count each failed/partial case once: `numeric` covers value, metric, period, scope,
  unit, or precision errors; `generation` covers other interpretation/completeness/faithfulness errors.
  `retrieval` identifies missing relevant context, with uncertainty about its upstream cause stated below.
  Secondary labels describe additional symptoms and are not added to the primary counts.
- The generation code sends all retrieved chunks in rank order. A generation label locates the observed
  error after retrieval; it does not prove the model's internal cause or exclude server-side truncation.

## Summary

| Type | Pass | Partial | Incorrect |
| --- | ---: | ---: | ---: |
| Narrative | 3 | 2 | 1 |
| Numeric | 2 | 1 | 3 |
| Multi-hop | 0 | 3 | 3 |
| No-answer | 6 | 0 | 0 |
| **Total** | **11** | **6** | **7** |

The 13 follow-up cases have primary labels: **numeric 5, generation 6, retrieval 2**.
Adobe's retrieval label is provisional. No case is assigned parser, chunking, or context as a confirmed
primary cause; this is not a claim that those stages are lossless.

This rubric is stricter than the earlier informal review: Pfizer multi-hop identifies both businesses
correctly but is now partial because it substitutes "sale" for "full disposition". Thus multi-hop has
zero unqualified passes here, rather than the earlier 1/6. This is a review change, not a new model result.
Likewise, the 6/6 abstention result below is rescoring, not an improvement in generated answers.

## Per-question labels

### nvda-2026-narrative
- Verdict: **incorrect**; primary: `generation`; confidence: high.
- Correctly names customer headquarters, but says this was the method "Prior to the change".
  R1 says "In the third quarter of fiscal year 2026, we changed to revenue based upon the location
  of our customers’ headquarters". It also omits the end-customer/shipping-location distinction.

### nvda-2026-numeric
- Verdict: **partial**; primary: `numeric`; secondary: `generation`; confidence: high.
- Answer: `$ 215.93`. R4 explicitly says `$215.9 billion`; its table has `$215,938` million.
  The magnitude is recognizable, but the requested one-decimal-place answer is not supplied.

### nvda-2026-multi-hop
- Verdict: **incorrect**; primary: `retrieval`; secondary: `numeric`, `generation`; confidence: high.
- None of R1-R5 supplies the requested 68% Data Center / 41% Gaming comparison (27 percentage points).
  Both passages appear together in R4 of `nvda-2026-numeric` in the same run, confirming index presence.
- The answer additionally mislabels R3's 142% Data Center **networking** growth as Gaming and invents
  a fiscal-2024 comparison. The 59% figure is for Data Center **computing**, not the whole platform.

### nvda-2026-no-answer
- Verdict: **pass**; primary: none.
- The full response is "Information not available in the provided context." It supplies no GPU count.

### amzn-2021-narrative
- Verdict: **pass**; primary: none.
- Describes recognizing AWS revenue when services are used, based on quantity delivered; supported by R2.

### amzn-2021-numeric
- Verdict: **incorrect**; primary: `numeric`; secondary: `generation`; confidence: high.
- Answer: `$168.0`. R1 explicitly states operating income was `$22.9 billion` for 2020 and contains
  the consolidated table value `$22,899` million. The correct evidence was already the first hit.

### amzn-2021-multi-hop
- Verdict: **partial**; primary: `generation`; confidence: high.
- Gives International's 40% growth only. R1 also provides North America's 38%; the answer omits
  the explicit comparison and the requested difference of 2 percentage points.

### amzn-2021-no-answer
- Verdict: **pass**; primary: none.
- The full response is "Information not available in the provided context." It supplies no member count.

### sbux-2019-narrative
- Verdict: **pass**; primary: none.
- Correctly identifies licensing CPG and Foodservice businesses to Nestlé.
  R1 also supports the stated offset from premium single-serve product revenue.

### sbux-2019-numeric
- Verdict: **incorrect**; primary: `numeric`; secondary: `generation`; confidence: high.
- Answer: `$3,485.2`. R3's dated columns have 2019 operating income `$3,782.8` and 2018 `$3,485.2`;
  the expected answer is `$3.8 billion`. R5 also contains the 2018 value, not the requested 2019 value.
- The strict quoted-passage match is false, but the equivalent 2019 table value is present.
  This is a limitation of the evidence metric, not proof of retrieval failure or answer correctness.

### sbux-2019-multi-hop
- Verdict: **incorrect**; primary: `numeric`; secondary: `generation`; confidence: high.
- Says Americas grew faster, using 20.7%. R1 gives International growth of 12%, R5 Americas growth of 9%.
  R5's 20.7% is operating income as a percentage of Americas revenues, not revenue growth.
  The required result is International by 3 percentage points.

### sbux-2019-no-answer
- Verdict: **pass**; primary: none.
- The full response is "Information not available in the provided context." It supplies no cup count.

### adbe-2018-narrative
- Verdict: **partial**; primary: `generation`; confidence: medium.
- Subscription, downloads, product examples, templates, tutorials, and pricing are supported by R2.
  It omits the reference's access across desktop, web, and mobile devices, also present in R2.
  This is a completeness issue under this rubric, not a fabricated description of Creative Cloud.

### adbe-2018-numeric
- Verdict: **pass**; primary: none.
- Answers `186 trillion`; R1 gives that number of data transactions in fiscal 2017.

### adbe-2018-multi-hop
- Verdict: **incorrect**; primary: `retrieval`; secondary: `generation`; confidence: medium.
- Answers with Adobe Experience Manager and Adobe Analytics Cloud instead of Digital Media and
  Digital Experience. R2 names the segments but does not give the requested role mapping; the other
  hits describe individual products. The complete top five do not establish both required mappings.
- Both gold passages survive in `data/eval-inspection/ADBE-2018/cleaned.txt`. Neither is a retrieved
  witness in any of this filing's four saved questions. The historical full index is not retained:
  retrieval/ranking is the probable bottleneck, but a chunk-construction contribution remains unverified.

### adbe-2018-no-answer
- Verdict: **pass**; primary: none.
- The full response is "Information not available in the provided context." It supplies no subscriber count.

### pfe-2015-narrative
- Verdict: **partial**; primary: `generation`; confidence: medium.
- Covers most regulatory areas but omits research, expressly included in R1's list.
  Approval requirements and post-marketing surveillance are supported by R2, so those additions
  are not treated as hallucinations. Approval alone does not explicitly cover the research facet.

### pfe-2015-numeric
- Verdict: **pass**; primary: none.
- Answers approximately 92%; R3 gives biopharmaceutical products' share of total 2014 revenues as 92%.

### pfe-2015-multi-hop
- Verdict: **partial**; primary: `generation`; confidence: medium.
- Correctly identifies Animal Health (2013) and Nutrition / Nestlé (2012), with both dates from R1.
  However, it calls Animal Health's exit a "sale" while R1 only establishes "full disposition".
  The more specific transaction wording is unsupported by the supplied context; preserve the source term.

### pfe-2015-no-answer
- Verdict: **pass**; primary: none; metric issue: original abstention false negative.
- Full response: "Information not found in the provided context." It supplies no patient count.
  The calibrated evaluator recognizes this refusal; the original saved `abstained` remains false.

### f-2014-narrative
- Verdict: **pass**; primary: none.
- Answers Ford and Lincoln, exactly the two brands named in R2.

### f-2014-numeric
- Verdict: **incorrect**; primary: `numeric`; secondary: `generation`; confidence: high.
- Answers a European brand-ranking fact from R2 instead of the requested U.S. market share.
  R1 explicitly gives U.S. share as 15.7% in 2013. This is wrong metric/geographic scope after retrieval.

### f-2014-multi-hop
- Verdict: **partial**; primary: `generation`; confidence: high.
- Describes Ford Credit / Other Financial Services instead of both requested operating sectors.
  R3 contains Automotive's vehicles/parts/accessories sales and Financial Services' interest on
  finance receivables; the answer omits Automotive. R1's financial subsegments appear to distract it.

### f-2014-no-answer
- Verdict: **pass**; primary: none.
- The full response is "Information not available in the provided context." It supplies no city sales count.

## Validation and limits

- Checked all 24 unique dev IDs against current questions: question, answer, evidence, type, ticker,
  year, and split match the saved records. All 24 have five retrieved chunks.
- Checked the six raw filing SHA-256 values against the manifest. Re-ran only parser and cleaner in
  a temporary directory: all six outputs are byte-identical to the saved inspection snapshots, and
  all answerable gold passages remain in cleaned text. This does not establish full parser coverage.
- Recomputed strict evidence flags from saved chunks: hit@5 stays 15/18 and multi-hop all-evidence@5
  stays 4/6. Recomputed abstention: 6/6 no-answer refusals and 0/18 false refusals; only Pfizer changes.
- Checked the quoted answer fragments, evidence ranks, cross-question NVIDIA witness, verdict totals,
  and primary-label totals. Baseline and gold files are unchanged; no live SEC/Ollama calls were needed.
- The single active index belongs to Ford. `index_metadata.json` still describes NVIDIA, so it is not
  used as proof of historical index contents. Server context settings and full per-filing indexes were
  not recorded by this run; exact ranking and server-side truncation cannot be reconstructed from it.
- The judgments above are an auditable AI review with explicit criteria, not new owner-confirmed gold.

## Next changes justified by this run

1. Prioritize numeric grounding: select metric, entity, period, value, and unit before formatting the
   answer. Use Starbucks' wrong-year and wrong-metric cases, Amazon income, and Ford geography as regressions.
2. Require both sides and the requested difference for comparisons; preserve source terminology and
   requested narrative facets. Amazon and Ford multi-hop already have both passages in a single hit.
3. Evaluate retrieval separately, with indexed chunks retained per filing. NVIDIA's missed known chunk
   is a confirmed retrieval target; inspect Adobe's full index before deciding on a chunking/ranking fix.
4. Compare candidate changes on dev with the same rubric and saved configuration, then perform the
   reserved test check after selecting the changes. No prompt, retrieval, or chunking fix is claimed here.
