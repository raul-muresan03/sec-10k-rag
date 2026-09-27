"""Regenerate or validate the committed dev evaluation replay snapshot."""

import argparse
import json
from pathlib import Path

from demo.export import DEFAULT_OUTPUT, build_snapshot, write_snapshot
from demo.public import validate_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Validate the committed snapshot without local runs")
    args = parser.parse_args()
    if args.check:
        validate_snapshot(json.loads(args.output.read_text(encoding="utf-8")))
        print(f"Validated {args.output}")
    else:
        write_snapshot(build_snapshot(), args.output)
        print(f"Exported {args.output}")


if __name__ == "__main__":
    main()
