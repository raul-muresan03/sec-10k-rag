# Evaluation Corpus v1

This directory defines the source material for the first evaluation set.
Each filing is selected by ticker and SEC filing year, not fiscal year. The
current ingestion downloads the newest non-amended `10-K` filed in that year.

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

The [draft evaluation questions](questions.jsonl) contain 40 records,
four per filing (24 dev, 16 test):

| Question type | Target |
| --- | ---: |
| Narrative | 10 |
| Numeric | 10 |
| Multi-hop | 10 |
| No-answer | 10 |
| **Total** | **40** |

Each filing will have one question of each type. No-answer cases require a
full-document search during manual verification. These questions and answers
were drafted with AI assistance. Their quoted evidence was matched to both
the selected SEC document and cleaned text, but they are **not yet a verified
gold set**: a human must confirm each answer, especially no-answer cases and
numeric values. Use dev to improve the application; reserve test for the
final check rather than tuning against it.

## Verification

Each selected ticker/year was downloaded through the current ingestion code,
and its SEC submission header confirms form `10-K` and the filing year.
See [the inspection notes](inspection.md) for parser and cleaner findings.
