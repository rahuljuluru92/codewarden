"""Human-readable rendering of the structured violation report."""
from __future__ import annotations


def format_report_text(report: dict) -> str:
    if report["total_findings"] == 0:
        return "No violations found."

    lines = [f"Found {report['total_findings']} violation(s):", ""]
    for finding in report["findings"]:
        location = finding["file_path"]
        if finding["start_line"]:
            location += f":{finding['start_line']}"
        lines.append(f"[{finding['severity'].upper()}] {location} — {finding['rule_id']}")
        lines.append(f"    {finding['message']}")
        if finding["status"] == "low_confidence_final":
            lines.append(f"    (low confidence: {finding['confidence']})")
        lines.append("")

    lines.append("Summary: " + ", ".join(f"{count} {severity}" for severity, count in report["by_severity"].items()))
    return "\n".join(lines)
