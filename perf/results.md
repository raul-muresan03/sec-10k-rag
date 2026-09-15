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

## ETL performance results after Ollama batching

- Command: `python3 perf/benchmark_batch_sizes.py`
- Model: `nomic-embed-text:latest`
- Model context: `2048 tokens`
- GPU: `NVIDIA GeForce RTX 4050 Laptop GPU`
- Total VRAM: `6141 MB`
- GPU sampling interval: `100 ms`
- Runs per batch size and mode: 1

Columns `VRAM min/max/avg` are measured usage in MB. GPU utilization columns are percentages.

## Warm start

Model loaded before measurements with `ollama run nomic-embed-text:latest warmup`.

| Batch size | Parsing | Cleaning | Chunking | Total ETL | VRAM min | VRAM max | VRAM avg | GPU util avg | GPU util max |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 0.04 s | 0.39 s | 16.41 s | 16.84 s | 1011 MB | 1104 MB | 1018.89 MB | 31.25% | 56% |
| 4 | 0.04 s | 0.31 s | 12.27 s | 12.63 s | 1015 MB | 1015 MB | 1015.00 MB | 37.82% | 61% |
| 8 | 0.04 s | 0.30 s | 10.91 s | 11.26 s | 1012 MB | 1018 MB | 1014.20 MB | 43.70% | 66% |
| 16 | 0.04 s | 0.32 s | 10.92 s | 11.28 s | 1012 MB | 1070 MB | 1032.49 MB | 46.66% | 62% |
| 32 | 0.04 s | 0.32 s | 10.26 s | 10.62 s | 1008 MB | 1056 MB | 1031.89 MB | 47.71% | 77% |
| 64 | 0.04 s | 0.31 s | 9.84 s | 10.19 s | 1034 MB | 1037 MB | 1035.66 MB | 48.84% | 65% |
| 128 | 0.04 s | 0.30 s | 9.89 s | 10.23 s | 1025 MB | 1037 MB | 1030.95 MB | 49.90% | 67% |
| 256 | 0.04 s | 0.34 s | 9.91 s | 10.29 s | 1022 MB | 1047 MB | 1032.80 MB | 49.55% | 70% |
| 512 | 0.04 s | 0.31 s | 9.76 s | 10.12 s | 1009 MB | 1030 MB | 1019.37 MB | 49.06% | 66% |
| 1024 | 0.04 s | 0.31 s | 9.81 s | 10.17 s | 1009 MB | 1029 MB | 1017.51 MB | 47.47% | 69% |

## Cold start

Model stopped with `ollama stop nomic-embed-text:latest` before every measurement. The first embedding request loaded the model.

| Batch size | Parsing | Cleaning | Chunking | Total ETL | VRAM min | VRAM max | VRAM avg | GPU util avg | GPU util max |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 0.04 s | 0.34 s | 18.30 s | 18.67 s | 569 MB | 1067 MB | 986.35 MB | 31.33% | 59% |
| 4 | 0.05 s | 0.33 s | 16.07 s | 16.44 s | 589 MB | 1076 MB | 989.63 MB | 35.34% | 58% |
| 8 | 0.04 s | 0.33 s | 14.66 s | 15.04 s | 625 MB | 1076 MB | 1000.34 MB | 37.30% | 56% |
| 16 | 0.04 s | 0.33 s | 14.39 s | 14.76 s | 593 MB | 1154 MB | 1017.24 MB | 42.78% | 76% |
| 32 | 0.04 s | 0.34 s | 15.42 s | 15.80 s | 662 MB | 1137 MB | 1020.09 MB | 45.07% | 69% |
| 64 | 0.04 s | 0.32 s | 14.28 s | 14.65 s | 633 MB | 1079 MB | 1002.73 MB | 43.79% | 72% |
| 128 | 0.04 s | 0.35 s | 13.61 s | 14.01 s | 611 MB | 1082 MB | 997.02 MB | 40.43% | 66% |
| 256 | 0.04 s | 0.31 s | 12.90 s | 13.26 s | 596 MB | 1049 MB | 964.59 MB | 35.74% | 64% |
| 512 | 0.04 s | 0.32 s | 13.01 s | 13.37 s | 587 MB | 1029 MB | 962.93 MB | 40.03% | 70% |
| 1024 | 0.04 s | 0.31 s | 12.74 s | 13.10 s | 588 MB | 1028 MB | 959.54 MB | 38.91% | 69% |

## Pareto analysis

Objectives: minimize total ETL time and peak VRAM usage. A scenario is Pareto-efficient when no other measured scenario has both lower or equal peak VRAM and lower or equal total ETL time. Each mode has one run per batch size, so results are directional.

| Mode | Pareto-efficient batch sizes | Fastest observed scenario | Practical choice from this run |
| --- | --- | --- | --- |
| Warm start | 4, 8, 512, 1024 | 512 → 10.12 s, 1030 MB peak | 512 |
| Cold start | 1024 | 1024 → 13.10 s, 1028 MB peak | 512 |

### Conclusion

Choose `EMBEDDING_BATCH_SIZE = 512` as the single production value. It is the fastest warm-start scenario at `10.12 s`, while cold start takes only `0.27 s` longer than batch `1024`. Batch `512` uses half as many inputs per request and has no meaningful observed VRAM disadvantage compared with batch `1024`.

Batch `1024` is fastest for cold start, but the gain is too small to justify using a larger batch as the application default.