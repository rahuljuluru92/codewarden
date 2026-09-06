"""codewarden CLI: run the architectural-compliance pipeline against a
target repo and a rules file.

    codewarden check <repo_path> --rules <rules.yaml> [--format json|text]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from codewarden.agents.graph import run_pipeline
from codewarden.cli.discovery import discover_source_files
from codewarden.cli.report_format import format_report_text
from codewarden.indexing.store import CodeIndex
from codewarden.parsing.parser import parse_source
from codewarden.rules.loader import load_ruleset

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codewarden", description="Multi-agent architectural compliance checker.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Check a repo against a rules file.")
    check.add_argument("repo_path", type=Path, help="Path to the repo to check.")
    check.add_argument("--rules", type=Path, required=True, help="Path to a rules YAML file.")
    check.add_argument("--format", choices=["text", "json"], default="text")
    check.add_argument(
        "--fail-on",
        choices=["error", "warning", "info", "never"],
        default="error",
        help="Exit with a non-zero status if a finding at or above this severity is found.",
    )
    return parser


def run_check(repo_path: Path, rules_path: Path) -> dict:
    if "GROQ_API_KEY" not in os.environ:
        print("Error: GROQ_API_KEY is not set. Export it or add it to a .env file.", file=sys.stderr)
        sys.exit(2)

    ruleset = load_ruleset(rules_path)

    source_files = discover_source_files(repo_path)
    if not source_files:
        print(f"No supported source files (.py, .ts, .tsx) found under {repo_path}", file=sys.stderr)

    parsed_files = {}
    for path in source_files:
        rel_path = str(path.relative_to(repo_path))
        parsed_files[rel_path] = parse_source(rel_path, path.read_text(encoding="utf-8"))

    index = CodeIndex(persist_path=tempfile.mkdtemp())
    for parsed in parsed_files.values():
        index.index_parsed_file(parsed)

    return run_pipeline(ruleset, parsed_files, index)


def _should_fail(report: dict, fail_on: str) -> bool:
    if fail_on == "never":
        return False
    threshold = SEVERITY_ORDER[fail_on]
    return any(SEVERITY_ORDER.get(f["severity"], 99) <= threshold for f in report["findings"])


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        report = run_check(args.repo_path, args.rules)

        if args.format == "json":
            print(json.dumps(report, indent=2))
        else:
            print(format_report_text(report))

        if _should_fail(report, args.fail_on):
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
