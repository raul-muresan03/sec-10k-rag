"""CLI entry point for preparing one manifest-verified dev filing."""

from pathlib import Path

from etl_pipeline.filing_store import FilingIndexStore


def ensure_index(ticker: str, year: int) -> Path:
    return FilingIndexStore().prepare_selected(ticker, year).index_path
