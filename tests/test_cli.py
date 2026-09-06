from pathlib import Path

from codewarden.cli.discovery import discover_source_files
from codewarden.cli.report_format import format_report_text

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GOLDEN_REPO = Path(__file__).resolve().parent.parent / "eval" / "golden_dataset" / "repo"


def test_discover_source_files_finds_py_and_ts(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.ts").write_text("const x = 1;\n")
    (tmp_path / "c.txt").write_text("not source\n")
    found = discover_source_files(tmp_path)
    assert {p.name for p in found} == {"a.py", "b.ts"}


def test_discover_source_files_skips_noise_dirs(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.ts").write_text("const x = 1;\n")
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "lib.py").write_text("x = 1\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "real.py").write_text("x = 1\n")

    found = discover_source_files(tmp_path)
    assert {p.name for p in found} == {"real.py"}


def test_discover_source_files_on_golden_dataset_repo():
    found = discover_source_files(GOLDEN_REPO)
    assert len(found) == 13


def test_format_report_text_no_findings():
    report = {"total_findings": 0, "by_severity": {}, "findings": []}
    assert format_report_text(report) == "No violations found."


def test_format_report_text_with_findings():
    report = {
        "total_findings": 1,
        "by_severity": {"error": 1},
        "findings": [
            {
                "rule_id": "no-controller-db-access",
                "severity": "error",
                "file_path": "app/x.py",
                "start_line": 5,
                "end_line": 5,
                "message": "bad import",
                "confidence": 1.0,
                "status": "confirmed",
            }
        ],
    }
    text = format_report_text(report)
    assert "ERROR" in text
    assert "app/x.py:5" in text
    assert "no-controller-db-access" in text
