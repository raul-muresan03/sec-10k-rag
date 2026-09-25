"""Commands for creating, summarizing, and comparing manual answer reviews."""

import argparse
import json
from pathlib import Path

from eval.answer_reviews import (
    compare_runs, create_review_template, load_reviewed_run, summarize_reviews,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Review saved answers; never infer correctness from evidence hits.")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("init", help="Create an unreviewed template for a saved answer run")
    create.add_argument("--run", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    summary = commands.add_parser("summarize", help="Count reviewed and unreviewed answers")
    summary.add_argument("--run", type=Path, required=True)
    summary.add_argument("--reviews", type=Path, required=True)
    compare = commands.add_parser("compare", help="Compare verdicts for shared reviewed questions")
    for prefix in ("baseline", "candidate"):
        compare.add_argument(f"--{prefix}-run", type=Path, required=True)
        compare.add_argument(f"--{prefix}-reviews", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            template = create_review_template(args.run)
            with args.output.open("x", encoding="utf-8") as target:
                json.dump(template, target, ensure_ascii=False, indent=2)
                target.write("\n")
            result = {"output": str(args.output), "questions": len(template["reviews"])}
        elif args.command == "summarize":
            run_id, records, reviews = load_reviewed_run(args.run, args.reviews)
            result = {"run_id": run_id, **summarize_reviews(records, reviews)}
        else:
            result = compare_runs(args.baseline_run, args.baseline_reviews, args.candidate_run, args.candidate_reviews)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
