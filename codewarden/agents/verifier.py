"""Verifier/Critic role: decides whether the batch of findings is trustworthy
enough to report, or whether some need another pass with more context.

This is the only role with visibility across the whole batch, so it's the
natural place to catch a low-confidence semantic verdict and re-queue it
rather than either silently reporting a guess or silently dropping it.
See DECISIONS.md (Stage 4 entry) for the full rationale.
"""
from __future__ import annotations

from codewarden.agents.models import Finding

DEFAULT_MAX_ITERATIONS = 2


def verify(
    findings: list[Finding],
    iteration: int,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    retried_task_keys: set[str] | None = None,
) -> tuple[list[Finding], list, set[str]]:
    """Returns (kept_findings, retry_tasks, updated_retried_task_keys)."""
    retried_task_keys = set(retried_task_keys or set())
    kept: list[Finding] = []
    retry_tasks = []

    for finding in findings:
        if finding.status == "ambiguous":
            if finding.task_key not in retried_task_keys and iteration < max_iterations:
                retry_tasks.append(finding.source_task)
                retried_task_keys.add(finding.task_key)
                continue  # dropped; a fresh finding replaces it after retry
            finding.status = "low_confidence_final"
        kept.append(finding)

    return kept, retry_tasks, retried_task_keys


def build_report(findings: list[Finding]) -> dict:
    severity_order = {"error": 0, "warning": 1, "info": 2}
    sorted_findings = sorted(
        findings,
        key=lambda f: (severity_order.get(f.severity, 99), f.file_path, f.start_line),
    )
    by_severity: dict[str, int] = {}
    for f in sorted_findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

    return {
        "total_findings": len(sorted_findings),
        "by_severity": by_severity,
        "findings": [
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "file_path": f.file_path,
                "start_line": f.start_line,
                "end_line": f.end_line,
                "message": f.message,
                "confidence": f.confidence,
                "status": f.status,
            }
            for f in sorted_findings
        ],
    }
