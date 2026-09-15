import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from etl_pipeline.parser import parse_10K
from etl_pipeline.cleaner import clean_10K
from etl_pipeline.chunker import chunk_10K


def benchmark_etl():
    pipeline_directory = PROJECT_ROOT / "etl_pipeline"
    raw_10K_path = PROJECT_ROOT / (
        "data/sec-edgar-filings/NVDA/10-K/0001045810-26-000021/full-submission.txt"
    )
    parsed_10K_path = PROJECT_ROOT / "data/output_parser.txt"
    chunked_10K_path = PROJECT_ROOT / "data/output_cleaner.txt"

    previous_directory = Path.cwd()
    os.chdir(pipeline_directory)
    try:
        start_time_etl = time.perf_counter()

        start_time_parse = time.perf_counter()
        parse_10K(file_path=str(raw_10K_path))
        end_time_parse = time.perf_counter()

        start_time_clean = time.perf_counter()
        clean_10K(file_path=str(parsed_10K_path))
        end_time_clean = time.perf_counter()

        start_time_chunk = time.perf_counter()
        chunk_10K(file_path=str(chunked_10K_path))
        end_time_chunk = time.perf_counter()

        end_time_etl = time.perf_counter()
    finally:
        os.chdir(previous_directory)

    total_parse = end_time_parse - start_time_parse
    total_clean = end_time_clean - start_time_clean
    total_chunk = end_time_chunk - start_time_chunk
    total_etl = end_time_etl - start_time_etl

    print(f"Total parsing time: {total_parse:.2f}")
    print(f"Total cleaning time: {total_clean:.2f}")
    print(f"Total chunking time: {total_chunk:.2f}")
    print(f"Total ETL time: {total_etl:.2f}")


if __name__ == "__main__":
    benchmark_etl()