import csv
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = PROJECT_ROOT / "perf/benchmark_etl.py"
MODEL = "nomic-embed-text:latest"
BATCH_SIZES = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
BENCHMARK_TIMEOUT_SECONDS = 300
GPU_SAMPLE_INTERVAL_SECONDS = 0.1

METRIC_PATTERN = re.compile(r"Total (parsing|cleaning|chunking|ETL) time: ([0-9.]+)")
METRIC_NAMES = {
    "parsing": "parsing_s",
    "cleaning": "cleaning_s",
    "chunking": "chunking_s",
    "ETL": "etl_s",
}


def query_gpu() -> dict[str, float | str] | None:
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    row = next(csv.reader(result.stdout.splitlines()), None)
    if row is None or len(row) != 4:
        return None

    try:
        return {
            "gpu_name": row[0].strip(),
            "vram_used_mb": float(row[1]),
            "vram_total_mb": float(row[2]),
            "gpu_utilization_pct": float(row[3]),
        }
    except ValueError:
        return None


def collect_gpu_samples(stop_event: threading.Event, samples: list[dict[str, float | str]]) -> None:
    while not stop_event.is_set():
        sample = query_gpu()
        if sample is not None:
            samples.append(sample)
        stop_event.wait(GPU_SAMPLE_INTERVAL_SECONDS)


def stop_model() -> None:
    subprocess.run(
        ["ollama", "stop", MODEL],
        cwd=PROJECT_ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def warm_model() -> None:
    stop_model()
    subprocess.run(
        ["ollama", "run", MODEL, "warmup"],
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def read_model_context_tokens() -> int:
    result = subprocess.run(
        ["ollama", "ps"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        fields = line.split()
        if fields and fields[0] == MODEL:
            return int(fields[6])
    raise RuntimeError(f"Model {MODEL} is not visible in ollama ps")


def run_benchmark(batch_size: int) -> dict[str, float | int]:
    environment = os.environ.copy()
    environment["EMBEDDING_BATCH_SIZE"] = str(batch_size)
    samples: list[dict[str, float | str]] = []
    stop_event = threading.Event()
    monitor = threading.Thread(target=collect_gpu_samples, args=(stop_event, samples), daemon=True)
    monitor.start()

    try:
        result = subprocess.run(
            [sys.executable, str(BENCHMARK)],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
            timeout=BENCHMARK_TIMEOUT_SECONDS,
        )
    finally:
        stop_event.set()
        monitor.join()

    metrics = {
        METRIC_NAMES[name]: float(value)
        for name, value in METRIC_PATTERN.findall(result.stdout)
    }
    expected = {"parsing_s", "cleaning_s", "chunking_s", "etl_s"}
    if set(metrics) != expected:
        raise RuntimeError(f"Could not parse benchmark output:\n{result.stdout}")
    if not samples:
        raise RuntimeError("No GPU samples collected")

    vram_values = [float(sample["vram_used_mb"]) for sample in samples]
    utilization_values = [float(sample["gpu_utilization_pct"]) for sample in samples]
    metrics.update(
        {
            "batch_size": batch_size,
            "vram_min_mb": min(vram_values),
            "vram_max_mb": max(vram_values),
            "vram_avg_mb": sum(vram_values) / len(vram_values),
            "gpu_utilization_avg_pct": sum(utilization_values) / len(utilization_values),
            "gpu_utilization_max_pct": max(utilization_values),
        }
    )
    return metrics


def run_warm_start() -> list[dict[str, float | int]]:
    warm_model()
    return [run_benchmark(batch_size) for batch_size in BATCH_SIZES]


def run_cold_start() -> list[dict[str, float | int]]:
    results = []
    for batch_size in BATCH_SIZES:
        stop_model()
        results.append(run_benchmark(batch_size))
    return results


def main() -> None:
    gpu = query_gpu()
    if gpu is None:
        raise RuntimeError("Could not read NVIDIA GPU metrics")

    warm_results = run_warm_start()
    context_tokens = read_model_context_tokens()
    cold_results = run_cold_start()
    measurements = {
        "gpu_name": gpu["gpu_name"],
        "vram_total_mb": gpu["vram_total_mb"],
        "model": MODEL,
        "context_tokens": context_tokens,
        "batch_sizes": BATCH_SIZES,
        "warm_start": warm_results,
        "cold_start": cold_results,
    }
    print(json.dumps(measurements, indent=2))


if __name__ == "__main__":
    main()
