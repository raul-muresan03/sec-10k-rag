import os
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from tests.support import PROJECT_ROOT


@pytest.fixture
def data_directory() -> Iterator[Path]:
    previous_directory = Path.cwd()
    with TemporaryDirectory() as temporary_directory:
        temporary_root = Path(temporary_directory)
        (temporary_root / "etl_pipeline").mkdir()
        data_directory = temporary_root / "data"
        data_directory.mkdir()
        os.chdir(temporary_root / "etl_pipeline")
        try:
            yield data_directory
        finally:
            os.chdir(previous_directory)
