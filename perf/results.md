# ETL performance results

## Initial baseline — 2026-09-15

- Branch: `perf/etl`
- Commit: `38d4688`
- Command: `python3 perf/benchmark_etl.py`
- Input: NVIDIA 10-K `0001045810-26-000021`
- Embedding model: `nomic-embed-text`
- Runs: 1

| Metric | Result |
| --- | ---: |
| Parsing time | 0.07 s |
| Cleaning time | 0.57 s |
| Chunking time | 29.52 s |
| Total ETL time | 30.17 s |