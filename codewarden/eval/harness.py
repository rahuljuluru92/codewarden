"""Runs the full multi-agent pipeline against the Golden Dataset and
computes real, reproducible precision/recall/F1 — see DECISIONS.md
(Stage 5 entry) for methodology and ground rule 4 (never fabricate an
eval number).

Usage (from repo root, with GROQ_API_KEY etc. exported):

    python -m codewarden.eval.harness
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from codewarden.agents.graph import run_pipeline
from codewarden.agents.llm_client import call_llm
from codewarden.eval.dataset import GoldenDataset, load_golden_dataset
from codewarden.eval.metrics import score
from codewarden.indexing.store import CodeIndex
from codewarden.rules.loader import load_ruleset
from codewarden.rules.matching import scope_matches

RULES_PATH = Path(__file__).resolve().parent.parent.parent / "rules" / "examples" / "example_rules.yaml"
RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "eval" / "results"


def validate_labels_cover_scope(dataset: GoldenDataset, ruleset) -> None:
    """Fail loudly if a rule's scope applies to a file with no ground-truth
    label, rather than silently skipping it and inflating the score."""
    missing = []
    for rule in ruleset.rules:
        rule_labels = dataset.labels.get(rule.id, {})
        for path, parsed in dataset.parsed_files.items():
            if parsed.language not in rule.languages:
                continue
            if not scope_matches(path, rule.scope.include, rule.scope.exclude):
                continue
            if path not in rule_labels:
                missing.append((rule.id, path))
    if missing:
        raise ValueError(f"Golden Dataset labels.yaml is missing ground truth for: {missing}")


def build_predicted(report: dict, ruleset, dataset: GoldenDataset) -> dict[tuple[str, str], bool]:
    predicted: dict[tuple[str, str], bool] = {}
    for rule in ruleset.rules:
        for path, parsed in dataset.parsed_files.items():
            if parsed.language not in rule.languages:
                continue
            if not scope_matches(path, rule.scope.include, rule.scope.exclude):
                continue
            predicted[(rule.id, path)] = False

    for finding in report["findings"]:
        key = (finding["rule_id"], finding["file_path"])
        if finding["status"] in ("confirmed", "low_confidence_final"):
            predicted[key] = True
    return predicted


def run_eval() -> dict:
    dataset = load_golden_dataset()
    ruleset = load_ruleset(RULES_PATH)
    validate_labels_cover_scope(dataset, ruleset)

    index = CodeIndex(persist_path=tempfile.mkdtemp())
    for parsed in dataset.parsed_files.values():
        index.index_parsed_file(parsed)

    usage_log = []

    def tracking_llm(prompt: str) -> str:
        response = call_llm(prompt)
        usage_log.append(
            {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "reasoning_tokens": response.usage.reasoning_tokens,
            }
        )
        return response.content

    start = time.monotonic()
    report = run_pipeline(ruleset, dataset.parsed_files, index, llm_fn=tracking_llm)
    elapsed = time.monotonic() - start

    predicted = build_predicted(report, ruleset, dataset)
    ground_truth = {
        (rule_id, path): violates for rule_id, file_labels in dataset.labels.items() for path, violates in file_labels.items()
    }

    overall = score(predicted, ground_truth)

    per_rule = {}
    for rule_id in dataset.labels:
        rule_predicted = {k: v for k, v in predicted.items() if k[0] == rule_id}
        rule_truth = {k: v for k, v in ground_truth.items() if k[0] == rule_id}
        per_rule[rule_id] = score(rule_predicted, rule_truth).as_dict()

    result = {
        "overall": overall.as_dict(),
        "per_rule": per_rule,
        "llm_calls": len(usage_log),
        "total_prompt_tokens": sum(u["prompt_tokens"] for u in usage_log),
        "total_completion_tokens": sum(u["completion_tokens"] for u in usage_log),
        "total_reasoning_tokens": sum(u["reasoning_tokens"] or 0 for u in usage_log),
        "elapsed_seconds": round(elapsed, 2),
        "num_labeled_pairs": len(ground_truth),
    }
    return result


def main() -> None:
    result = run_eval()
    print(json.dumps(result, indent=2))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"eval_{int(time.time())}.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
