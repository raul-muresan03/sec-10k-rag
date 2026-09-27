"""Evaluation provenance and isolated index helpers."""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import etl_pipeline
from etl_pipeline.filings import MANIFEST_PATH, VerifiedFiling, hash_file, verify_filings
from etl_pipeline.indexing import build_index, index_configuration


@contextmanager
def use_index_directory(path: Path) -> Iterator[None]:
    previous = etl_pipeline.DATA_DIR
    etl_pipeline.DATA_DIR = path
    try:
        yield
    finally:
        etl_pipeline.DATA_DIR = previous
