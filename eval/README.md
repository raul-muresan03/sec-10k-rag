# Evaluation Corpus v1

This directory defines the source material for the first evaluation set. This
initial version selects the filings only; the corpus manifest, local file
paths, checksums, and dev/test split belong to later tasks.

## Selection Rules

- Include exactly 10 filings from 10 companies and several industries.
- Use Form `10-K` only; exclude amendments such as `10-K/A`.
- Cover legacy, transitional, and modern filing layouts.
- Prefer filings that can support narrative, numeric, and multi-hop questions.

For this corpus, legacy means filed through 2015, transitional means filed
from 2016 through 2020, and modern means filed from 2021 onward. These are
time-based selection buckets, not parser-quality claims. The later manual
audit will record the actual structure and any parser data loss.

## Selected Filings

### NVIDIA CORP (NVDA)

- Identity: CIK `0001045810`; industry: semiconductors; layout: modern.
- Filing: [`0001045810-26-000021`][nvda]; filed 2026-02-25; report period 2026-01-25.
- Coverage: narrative and numeric.
- Rationale: recent Inline XBRL filing with extensive risk disclosures and financial tables.

### Apple Inc. (AAPL)

- Identity: CIK `0000320193`; industry: consumer technology; layout: modern.
- Filing: [`0000320193-24-000123`][apple]; filed 2024-11-01; report period 2024-09-28.
- Coverage: numeric and multi-hop.
- Rationale: adds product and geographic reporting in a recent large-company filing.

### JPMORGAN CHASE & CO (JPM)

- Identity: CIK `0000019617`; industry: financial services; layout: modern.
- Filing: [`0000019617-23-000231`][jpm]; filed 2023-02-21; report period 2022-12-31.
- Coverage: numeric and multi-hop.
- Rationale: adds a regulated financial company with dense tables and linked disclosures.

### AMAZON COM INC (AMZN)

- Identity: CIK `0001018724`; industry: retail and cloud services; layout: modern.
- Filing: [`0001018724-21-000004`][amazon]; filed 2021-02-03; report period 2020-12-31.
- Coverage: narrative and multi-hop.
- Rationale: adds distinct business segments and cross-section relationships.

### STARBUCKS CORP (SBUX)

- Identity: CIK `0000829224`; industry: restaurants; layout: transitional.
- Filing: [`0000829224-19-000051`][starbucks]; filed 2019-11-15; report period 2019-09-29.
- Coverage: narrative and numeric.
- Rationale: adds an off-calendar fiscal year and store and segment disclosures.

### EXXON MOBIL CORP (XOM)

- Identity: CIK `0000034088`; industry: energy; layout: transitional.
- Filing: [`0000034088-19-000010`][exxon]; filed 2019-02-27; report period 2018-12-31.
- Coverage: numeric and multi-hop.
- Rationale: adds an asset-heavy company with commodity, reserves, and segment disclosures.

### MICROSOFT CORP (MSFT)

- Identity: CIK `0000789019`; industry: software; layout: transitional.
- Filing: [`0001564590-18-019062`][microsoft]; filed 2018-08-03; report period 2018-06-30.
- Coverage: narrative and numeric.
- Rationale: adds a transition-era filing with software and cloud segment reporting.

### PFIZER INC (PFE)

- Identity: CIK `0000078003`; industry: pharmaceuticals; layout: legacy.
- Filing: [`0000078003-15-000014`][pfizer]; filed 2015-02-27; report period 2014-12-31.
- Coverage: narrative and multi-hop.
- Rationale: adds legacy pharmaceutical disclosures about products, patents, and regulation.

### FORD MOTOR CO (F)

- Identity: CIK `0000037996`; industry: automotive; layout: legacy.
- Filing: [`0000037996-14-000010`][ford]; filed 2014-02-18; report period 2013-12-31.
- Coverage: narrative and numeric.
- Rationale: adds a legacy industrial filing with automotive, credit, and pension data.

### Walmart Inc. (WMT)

- Identity: CIK `0000104169`; industry: retail; layout: legacy.
- Filing: [`0000104169-14-000019`][walmart]; filed 2014-03-21; report period 2014-01-31.
- Coverage: numeric and multi-hop.
- Rationale: adds a legacy retail filing with an off-calendar year and segment disclosures.

## Evaluation Target

The later evaluation dataset will contain 40 manually verified questions:

| Question type | Target |
| --- | ---: |
| Narrative | 14 |
| Numeric | 12 |
| Multi-hop | 8 |
| No-answer | 6 |
| **Total** | **40** |

No-answer questions are not assigned to individual filings at selection time.
They require a full-document search during manual verification.

## Verification

The filing metadata was checked against the SEC submissions data for each
company. Every selected record has form exactly `10-K`, and each linked SEC
filing page returned HTTP 200 when requested with the project's SEC contact
user agent. The legacy records were verified in the historical submissions
files referenced by the corresponding company submissions data.

[nvda]: https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.html
[apple]: https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123-index.html
[jpm]: https://www.sec.gov/Archives/edgar/data/19617/000001961723000231/0000019617-23-000231-index.html
[amazon]: https://www.sec.gov/Archives/edgar/data/1018724/000101872421000004/0001018724-21-000004-index.html
[starbucks]: https://www.sec.gov/Archives/edgar/data/829224/000082922419000051/0000829224-19-000051-index.html
[exxon]: https://www.sec.gov/Archives/edgar/data/34088/000003408819000010/0000034088-19-000010-index.html
[microsoft]: https://www.sec.gov/Archives/edgar/data/789019/000156459018019062/0001564590-18-019062-index.html
[pfizer]: https://www.sec.gov/Archives/edgar/data/78003/000007800315000014/0000078003-15-000014-index.html
[ford]: https://www.sec.gov/Archives/edgar/data/37996/000003799614000010/0000037996-14-000010-index.html
[walmart]: https://www.sec.gov/Archives/edgar/data/104169/000010416914000019/0000104169-14-000019-index.html
