import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NVIDIA_PARSED_10K = PROJECT_ROOT / "data/output_parser.txt"

for import_path in (PROJECT_ROOT, PROJECT_ROOT / "etl_pipeline"):
    path_text = str(import_path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)
