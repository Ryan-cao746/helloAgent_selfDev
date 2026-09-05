"""Command line interface for the lightweight BFCL runner."""

from __future__ import annotations

import argparse
import sys

from project1.evaluation.bfcl.runner import (
    DEFAULT_OUTPUT_ROOT,
    official_evaluate_command,
    run_bfcl_file,
    validate_result_file,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate lightweight BFCL result files for project1."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="generate BFCL result files")
    run_parser.add_argument("--dataset", required=True, help="BFCL JSONL dataset path")
    run_parser.add_argument("--category", required=True, help="BFCL test category")
    run_parser.add_argument(
        "--model-name",
        default="helloagent_prompt",
        help="Model name used in the output directory",
    )
    run_parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help="Output root for result/traces/summaries",
    )
    run_parser.add_argument("--limit", type=int, default=None)
    run_parser.add_argument("--temperature", type=float, default=0)
    run_parser.add_argument("--decision-retries", type=int, default=1)

    validate_parser = subparsers.add_parser(
        "validate",
        help="validate a generated BFCL result file",
    )
    validate_parser.add_argument("--results", required=True)

    command_parser = subparsers.add_parser(
        "official-command",
        help="print the official bfcl evaluate command for generated results",
    )
    command_parser.add_argument("--model-name", required=True)
    command_parser.add_argument("--category", required=True)
    command_parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    command_parser.add_argument(
        "--full-eval",
        action="store_true",
        help="omit --partial-eval from the printed command",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        summary = run_bfcl_file(
            args.dataset,
            category=args.category,
            model_name=args.model_name,
            output_root=args.output_root,
            limit=args.limit,
            temperature=args.temperature,
            decision_retries=args.decision_retries,
        )
        print(summary.model_dump_json(indent=2))
        return 0

    if args.command == "validate":
        valid, errors = validate_result_file(args.results)
        if valid:
            print("BFCL result file is valid.")
            return 0
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    if args.command == "official-command":
        print(
            official_evaluate_command(
                model_name=args.model_name,
                category=args.category,
                output_root=args.output_root,
                partial_eval=not args.full_eval,
            )
        )
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
