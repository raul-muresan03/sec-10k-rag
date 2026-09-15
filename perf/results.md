# ETL performance results

## Initial baseline — 2026-09-15

- Branch: `perf/etl`
- Commit: `38d4688`
- Command: `python3 perf/benchmark_etl.py`
- Input: NVIDIA 10-K `0001045810-26-000021`
- Embedding model: `nomic-embed-text`
- Runs: 5

| Run | Parsing time | Cleaning time | Chunking time | Total ETL time |
| --- | ---: | ---: | ---: | ---: |
| Run 1 | 0.07 s | 0.57 s | 29.52 s | 30.17 s |
| Run 2 | 0.06 s | 0.59 s | 28.47 s | 29.14 s |
| Run 3 | 0.07 s | 0.55 s | 26.88 s | 27.51 s |
| Run 4 | 0.07 s | 0.56 s | 27.02 s | 27.66 s |
| Run 5 | 0.07 s | 0.57 s | 25.81 s | 26.46 s |
| **Min** | **0.06 s** | **0.55 s** | **25.81 s** | **26.46 s** |
| **Max** | **0.07 s** | **0.59 s** | **29.52 s** | **30.17 s** |
| **Avg** | **0.07 s** | **0.57 s** | **27.54 s** | **28.19 s** |
