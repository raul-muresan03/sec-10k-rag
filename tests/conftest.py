from pathlib import Path

import pytest

import etl_pipeline


@pytest.fixture
def data_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    monkeypatch.setattr(etl_pipeline, "DATA_DIR", data_directory)
    return data_directory
