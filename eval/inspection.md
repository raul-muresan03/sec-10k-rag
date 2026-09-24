# Corpus inspection (v1)

This is a spot-check of the ten ticker/year pairs in [README.md](README.md),
using the existing `download_10k`, `parse_10K`, and `clean_10K` functions.
The raw SEC submissions, parser output, and cleaner output remain under ignored
`data/` paths. Parser and cleaner were run once per filing; their shared output
files were copied to `data/eval-inspection/<TICKER>-<YEAR>/` before the next run.
The notes below compare the selected `10-K` document with its cleaned text;
they are not an exhaustive audit of every cell or statement.

All ten downloads succeeded. Their submission headers report form `10-K`,
and `FILED AS OF DATE` falls within the year listed in the corpus. All ten
documents parsed and cleaned without exceptions. Table counts below describe
HTML `<table>` elements and rendered Markdown tables, not a completeness score:
nested or empty tables can account for differences.

## Dev

### NVDA 2026 — usable, with navigation noise

- **Headings:** Item 1, Item 1A, Item 7 and Item 8 remain visible; note headings remain.
- **Tables / notes:** 64 HTML tables and 64 rendered tables; Note 1 is present.
  Ten cells have `rowspan`, which the cleaner does not reconstruct.
- **Repetition:** The company/subsidiary header recurs roughly 31 times;
  around 84 bare page-number lines remain in cleaned text.
- **Loss:** The cleaner deletes links, including visible table-of-contents
  titles; the source contains a linked "Consolidated Statements of Income"
  title absent in that form from cleaned text. Check evidence against the
  substantive section rather than the table of contents.

### AMZN 2021 — usable, check linked text

- **Headings:** Item sections and numbered notes remain findable in cleaned text.
- **Tables / notes:** 83 HTML tables and 81 rendered tables; Note 1 through
  Note 3 headings remain. The difference alone does not prove table loss.
- **Repetition:** "See accompanying notes to consolidated financial statements"
  occurs five times; table-of-contents material survives in part.
- **Loss:** Links are deleted with their visible text (for example "Table of
  Contents" links); verify a chosen source passage is still in cleaned text.

### SBUX 2019 — usable, check table alignment

- **Headings:** Item 1, Item 1A and numbered notes remain visible.
- **Tables / footnotes:** 206 HTML tables and 91 rendered tables; 75 cells
  use `rowspan`, and 102 `<sup>` elements include note markers and trademarks.
  The cleaner does not preserve row-span relationships or superscript markup.
- **Repetition / loss:** "See notes to consolidated financial statements"
  occurs five times. Table-of-contents links lose their text; check the
  financial row and its footnote directly before using a numeric answer.

### ADBE 2018 — usable, check repeated headers

- **Headings:** Item 7 and numbered notes are visible in the cleaned text;
  subscription, Creative Cloud and Digital Experience passages remain.
- **Tables / footnotes:** 201 HTML tables and 95 rendered tables; five cells
  use `rowspan` and 68 `<sup>` elements lose their original markup. Confirm
  the meaning of numeric rows before using them as evidence.
- **Repetition / loss:** "ADOBE SYSTEMS INCORPORATED" repeats about 42 times
  and the continued financial-notes header about 34 times. Links lose their
  visible text. This filing replaces MSFT 2018: its cleaned output retained
  no substantive standalone paragraphs, because the cleaner skips `<p>` text
  outside terminal `<div>` elements.

### PFE 2015 — conditional: financial annex excluded

- **Headings:** Item references are present; many financial section titles
  appear as references to a separate annual financial report.
- **Tables / footnotes:** 70 HTML tables and 38 rendered tables; 27 `<sup>`
  elements include numbered markers, whose superscript formatting is lost.
- **Repetition / loss:** The main `10-K` repeatedly incorporates the 2014
  Financial Report by reference. That report is in a separate `EX-13` document
  in the downloaded submission; `parse_10K` selects only `TYPE=10-K`.
  Financial-note evidence in `EX-13` is therefore unavailable to retrieval.
  Use only evidence found in the cleaned main document, or revisit this filing.

### F 2014 — usable, with substantial repetition

- **Headings:** Item 1 and Note 1 remain; continued Item 1 and Item 7
  headings recur across pages.
- **Tables / notes:** 461 HTML tables and 156 rendered tables; notes to the
  financial statements and some numeric rows remain. The count difference
  needs row-level checking before numeric questions are accepted.
- **Repetition:** "Ford Motor Company and Subsidiaries" repeats about 80
  times; "Notes to the Financial Statements" about 72 times, and the Item 7
  header about 51 times. This can crowd out other retrieval hits.
- **Loss:** Page/heading hierarchy and the meaning of table spans are not
  retained as structure; verify the exact evidence line after cleaning.

## Test

### AAPL 2024 — usable, check linked statement titles

- **Headings:** Item 1, Item 1A, Item 7 and numbered notes remain visible.
- **Tables / notes:** 63 HTML tables and 55 rendered tables; 12 cells use
  `rowspan`, which is not reconstructed.
- **Repetition / loss:** The notes cross-reference recurs five times. Linked
  table-of-contents text for "Consolidated Statements of Operations for the
  years ended September 28, 2024" is absent in that form after link removal;
  use a passage from the actual statement, not its navigation entry.

### JPM 2023 — usable, high table-alignment risk

- **Headings:** Item 1, Item 1A, Item 7, Item 8 and numbered notes survive.
- **Tables / footnotes:** 640 HTML tables and 639 rendered tables; 234 cells
  use `rowspan`. The cleaner expands `colspan` but ignores `rowspan`, so verify
  each numeric row against the source before using it as gold evidence.
- **Repetition / loss:** "Notes to consolidated financial statements" repeats
  roughly 64 times and the MD&A header roughly 55 times. Links are removed,
  and some visible link labels (e.g. "Return on equity and assets") disappear.

### CVX 2019 — usable, check footnote links

- **Headings:** Item 1, Item 1A, Item 7 and numbered notes remain visible.
- **Tables / footnotes:** 171 HTML tables and 115 rendered tables; 12 cells
  use `rowspan`, and 273 `<sup>` elements contain footnote-like markers or
  symbols. Their structure is flattened by the cleaner.
- **Repetition / loss:** "Millions of dollars, except per-share amounts"
  recurs about 37 times and the notes header about 35 times. The linked label
  "Financial ratios" does not survive link removal; check actual table text.
- **Corpus change:** XOM 2019 was replaced here. SEC lists XOM's `10-K`, but
  `download_10k("XOM", 2019)` returned no filing using the current downloader.
  `download_10k("CVX", 2019)` succeeded without changing application code.

### WMT 2014 — conditional: financial annex excluded

- **Headings:** Item 1 and Item 8 are referenced in the main filing; many
  detailed financial statements are incorporated by reference.
- **Tables / footnotes:** 73 HTML tables and 43 rendered tables; 16 `<sup>`
  elements include numbered markers whose superscript relationship is lost.
- **Repetition / loss:** The main `10-K` refers to the annual report and
  its consolidated financial statements. The submission has a separate
  `EX-13` document with that material, but `parse_10K` discards it.
  Do not use the annex as gold evidence for the current RAG pipeline.

## Implications for question writing

- Check the answer and supporting passage against **both** the raw SEC source
  and cleaned output. A source-only answer tests extraction failure, not RAG.
- Avoid financial details present only in the PFE/WMT `EX-13` annexes.
  Replace a filing if four
  verifiable questions cannot be written from text available to retrieval.
- For numeric and multi-hop cases, confirm table values, units, periods and
  footnote references in the raw source; flattened tables may shift context.
- No-answer status requires a whole-submission check, including other
  document blocks; missing text in the cleaner is not evidence of no answer.
