"""Live-LLM integration test: hits the real Groq API. Excluded from the
default fast suite (see pyproject.toml `addopts = "-m 'not live'"`); run
explicitly with `pytest -m live`.
"""
from pathlib import Path

import pytest

from codewarden.agents.graph import run_pipeline
from codewarden.indexing.store import CodeIndex
from codewarden.parsing.parser import parse_source
from codewarden.rules.loader import load_ruleset

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "examples" / "example_rules.yaml"

PATH_MAP = {
    "app/controllers/user_controller.py": "user_controller.py",
    "app/services/order_service.py": "order_service.py",
}


@pytest.mark.live
def test_pipeline_end_to_end_with_real_groq_api(tmp_path):
    parsed_files = {
        fake_path: parse_source(fake_path, (FIXTURES / real_name).read_text())
        for fake_path, real_name in PATH_MAP.items()
    }
    index = CodeIndex(persist_path=str(tmp_path / "chroma_db"))
    for parsed in parsed_files.values():
        index.index_parsed_file(parsed)

    ruleset = load_ruleset(RULES_PATH)
    report = run_pipeline(ruleset, parsed_files, index)

    assert report is not None
    assert "no-controller-db-access" in {f["rule_id"] for f in report["findings"]}
