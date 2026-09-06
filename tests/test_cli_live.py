"""Live CLI integration test: installs and runs the real `codewarden`
console script end-to-end against a sample repo, hitting the real Groq
API. Excluded from the default fast suite; run with `pytest -m live`.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_REPO = REPO_ROOT / "eval" / "golden_dataset" / "repo"
RULES_PATH = REPO_ROOT / "rules" / "examples" / "example_rules.yaml"


@pytest.mark.live
def test_cli_check_runs_end_to_end_against_sample_repo():
    result = subprocess.run(
        [
            "codewarden",
            "check",
            str(GOLDEN_REPO),
            "--rules",
            str(RULES_PATH),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=180,
    )

    assert result.returncode == 1, result.stderr  # error-severity findings exist in the golden repo
    report = json.loads(result.stdout)
    assert report["total_findings"] > 0
    rule_ids = {f["rule_id"] for f in report["findings"]}
    assert "no-controller-db-access" in rule_ids


@pytest.mark.live
def test_cli_check_fail_on_never_always_exits_zero():
    result = subprocess.run(
        [
            "codewarden",
            "check",
            str(GOLDEN_REPO),
            "--rules",
            str(RULES_PATH),
            "--format",
            "json",
            "--fail-on",
            "never",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr
