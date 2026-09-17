import subprocess
import sys

from tests.support import PROJECT_ROOT


def test_package_imports_from_project_root():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import etl_pipeline.parser, etl_pipeline.cleaner, etl_pipeline.chunker, "
            "etl_pipeline.vector_store, etl_pipeline.rag_engine, etl_pipeline.ingest",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
