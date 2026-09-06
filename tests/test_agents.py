from pathlib import Path

import pytest

from codewarden.agents.analyzer import analyze_task
from codewarden.agents.graph import run_pipeline
from codewarden.agents.models import AnalysisTask
from codewarden.agents.planner import build_initial_tasks, expand_task_context, plan
from codewarden.agents.verifier import build_report, verify
from codewarden.indexing.store import CodeIndex
from codewarden.parsing.parser import parse_source
from codewarden.rules.loader import load_ruleset

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "examples" / "example_rules.yaml"

# Fixture paths deliberately mimic the directory layout the example rules'
# scope globs expect (controllers/, services/), unlike the Stage 2/3
# fixtures which used bare filenames.
PATH_MAP = {
    "app/controllers/user_controller.py": "user_controller.py",
    "app/controllers/user_controller.ts": "user_controller.ts",
    "app/services/order_service.py": "order_service.py",
    "app/utils/math_utils.py": "math_utils.py",
}


@pytest.fixture()
def parsed_files():
    return {
        fake_path: parse_source(fake_path, (FIXTURES / real_name).read_text())
        for fake_path, real_name in PATH_MAP.items()
    }


@pytest.fixture()
def index(tmp_path, parsed_files):
    idx = CodeIndex(persist_path=str(tmp_path / "chroma_db"))
    for parsed in parsed_files.values():
        idx.index_parsed_file(parsed)
    return idx


@pytest.fixture()
def ruleset():
    return load_ruleset(RULES_PATH)


def confident_llm(prompt: str) -> str:
    return '{"violates": true, "explanation": "mocked violation", "confidence": 0.9}'


def clean_llm(prompt: str) -> str:
    return '{"violates": false, "explanation": "looks fine", "confidence": 0.95}'


# --------------------------------------------------------------------------
# Planner
# --------------------------------------------------------------------------


def test_planner_resolves_structural_tasks_by_scope(parsed_files, index, ruleset):
    tasks = build_initial_tasks(ruleset, parsed_files, index)
    import_restriction_tasks = [t for t in tasks if t.rule.id == "no-controller-db-access"]
    # rule is scoped to languages: [python], so the .ts controller is excluded
    assert {t.file_path for t in import_restriction_tasks} == {
        "app/controllers/user_controller.py",
    }


def test_planner_resolves_semantic_tasks_via_retrieval(parsed_files, index, ruleset):
    tasks = build_initial_tasks(ruleset, parsed_files, index)
    semantic_tasks = [t for t in tasks if t.rule.id == "no-business-logic-in-controllers"]
    assert len(semantic_tasks) > 0


def test_planner_semantic_tasks_cover_every_in_scope_file(parsed_files, index, ruleset):
    """Regression test for the Stage 6 retrieval-starvation bug: a single
    global top-N query across all in-scope files let some files' functions
    get crowded out entirely by other files' chunks that merely embedded
    closer to the check_prompt (see DECISIONS.md, Stage 6 iteration #1).
    Every in-scope file must get at least one task planned."""
    rule = next(r for r in ruleset.rules if r.id == "no-business-logic-in-controllers")
    tasks = build_initial_tasks(ruleset, parsed_files, index)
    semantic_tasks = [t for t in tasks if t.rule.id == rule.id]
    covered_files = {t.file_path for t in semantic_tasks}
    expected_files = {
        "app/controllers/user_controller.py",
        "app/controllers/user_controller.ts",
    }
    assert expected_files.issubset(covered_files)
    assert all(t.chunk_id is not None for t in semantic_tasks)
    assert all(t.file_path.startswith("app/controllers/") for t in semantic_tasks)


def test_planner_expand_task_context_widens_retrieval(parsed_files, index, ruleset):
    tasks = build_initial_tasks(ruleset, parsed_files, index)
    semantic_task = next(t for t in tasks if t.rule.id == "no-business-logic-in-controllers")
    expanded = expand_task_context(semantic_task, index)
    assert expanded.expand_context is True
    assert expanded.chunk_id == semantic_task.chunk_id


# --------------------------------------------------------------------------
# Executor / Analyzer
# --------------------------------------------------------------------------


def test_analyzer_import_restriction_detects_forbidden_import(parsed_files, ruleset):
    rule = next(r for r in ruleset.rules if r.id == "no-controller-db-access")
    task = AnalysisTask(rule=rule, file_path="app/controllers/user_controller.py")
    findings = analyze_task(task, parsed_files)
    assert len(findings) == 1
    assert findings[0].status == "confirmed"
    assert findings[0].confidence == 1.0


def test_analyzer_import_restriction_no_violation_for_clean_file(parsed_files, ruleset):
    rule = next(r for r in ruleset.rules if r.id == "no-controller-db-access")
    task = AnalysisTask(rule=rule, file_path="app/services/order_service.py")
    findings = analyze_task(task, parsed_files)
    assert findings == []


def test_analyzer_semantic_check_uses_injected_llm(parsed_files, ruleset):
    rule = next(r for r in ruleset.rules if r.id == "no-business-logic-in-controllers")
    task = AnalysisTask(
        rule=rule,
        file_path="app/controllers/user_controller.py",
        chunk_id="fake-chunk",
        chunk_text="def get_user(self, user_id): ...",
    )
    findings = analyze_task(task, parsed_files, llm_fn=confident_llm)
    assert len(findings) == 1
    assert findings[0].status == "confirmed"

    findings_clean = analyze_task(task, parsed_files, llm_fn=clean_llm)
    assert findings_clean == []


def test_analyzer_low_confidence_verdict_marked_ambiguous(parsed_files, ruleset):
    rule = next(r for r in ruleset.rules if r.id == "no-business-logic-in-controllers")
    task = AnalysisTask(
        rule=rule,
        file_path="app/controllers/user_controller.py",
        chunk_id="fake-chunk",
        chunk_text="def get_user(self, user_id): ...",
    )
    unsure_llm = lambda prompt: '{"violates": true, "explanation": "not sure", "confidence": 0.5}'
    findings = analyze_task(task, parsed_files, llm_fn=unsure_llm)
    assert len(findings) == 1
    assert findings[0].status == "ambiguous"


# --------------------------------------------------------------------------
# Verifier
# --------------------------------------------------------------------------


def test_verifier_requeues_ambiguous_findings_for_retry(parsed_files, ruleset):
    rule = next(r for r in ruleset.rules if r.id == "no-business-logic-in-controllers")
    task = AnalysisTask(rule=rule, file_path="app/controllers/user_controller.py", chunk_id="c1", chunk_text="...")
    from codewarden.agents.models import Finding

    ambiguous = Finding(
        task_key=task.key,
        rule_id=rule.id,
        severity=rule.severity,
        file_path=task.file_path,
        start_line=0,
        end_line=0,
        message="unsure",
        confidence=0.5,
        status="ambiguous",
        source_task=task,
    )
    kept, retry_tasks, retried_keys = verify([ambiguous], iteration=1, max_iterations=2)
    assert kept == []
    assert retry_tasks == [task]
    assert task.key in retried_keys


def test_verifier_gives_up_after_max_iterations(parsed_files, ruleset):
    rule = next(r for r in ruleset.rules if r.id == "no-business-logic-in-controllers")
    task = AnalysisTask(rule=rule, file_path="app/controllers/user_controller.py", chunk_id="c1", chunk_text="...")
    from codewarden.agents.models import Finding

    ambiguous = Finding(
        task_key=task.key,
        rule_id=rule.id,
        severity=rule.severity,
        file_path=task.file_path,
        start_line=0,
        end_line=0,
        message="still unsure",
        confidence=0.5,
        status="ambiguous",
        source_task=task,
    )
    kept, retry_tasks, _ = verify([ambiguous], iteration=2, max_iterations=2)
    assert retry_tasks == []
    assert len(kept) == 1
    assert kept[0].status == "low_confidence_final"


def test_build_report_groups_and_sorts_by_severity():
    from codewarden.agents.models import Finding

    dummy_task = AnalysisTask(rule=None, file_path="x")  # not used by build_report
    f_warning = Finding("k1", "r1", "warning", "b.py", 1, 1, "msg", 0.9, "confirmed", dummy_task)
    f_error = Finding("k2", "r2", "error", "a.py", 2, 2, "msg", 1.0, "confirmed", dummy_task)
    report = build_report([f_warning, f_error])
    assert report["total_findings"] == 2
    assert report["by_severity"] == {"warning": 1, "error": 1}
    assert report["findings"][0]["severity"] == "error"  # errors sort first


# --------------------------------------------------------------------------
# End-to-end DAG orchestration
# --------------------------------------------------------------------------


def test_pipeline_runs_end_to_end_and_produces_structured_report(parsed_files, index, ruleset):
    report = run_pipeline(ruleset, parsed_files, index, llm_fn=confident_llm)
    assert report["total_findings"] > 0
    assert "no-controller-db-access" in {f["rule_id"] for f in report["findings"]}
    assert all(f["status"] == "confirmed" for f in report["findings"])


def test_pipeline_retries_ambiguous_findings_then_resolves(parsed_files, index, ruleset):
    calls = {"n": 0}

    def flaky_llm(prompt: str) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            return '{"violates": true, "explanation": "unsure", "confidence": 0.5}'
        return '{"violates": true, "explanation": "confirmed on retry", "confidence": 0.9}'

    # Restrict to one file so there's exactly one semantic task, making the
    # retry behavior deterministic to assert on.
    import tempfile

    single_file = {"app/controllers/user_controller.py": parsed_files["app/controllers/user_controller.py"]}
    idx = CodeIndex(persist_path=tempfile.mkdtemp())
    idx.index_parsed_file(single_file["app/controllers/user_controller.py"])

    report = run_pipeline(ruleset, single_file, idx, llm_fn=flaky_llm)

    assert calls["n"] >= 2  # at least one retry happened
    business_logic_findings = [f for f in report["findings"] if f["rule_id"] == "no-business-logic-in-controllers"]
    assert len(business_logic_findings) > 0
    assert all(f["status"] == "confirmed" for f in business_logic_findings)


def test_pipeline_unparseable_llm_response_does_not_crash(parsed_files, index, ruleset):
    def garbage_llm(prompt: str) -> str:
        return "not json at all"

    report = run_pipeline(ruleset, parsed_files, index, llm_fn=garbage_llm)
    # unparseable verdicts stay ambiguous, retry, then get reported as
    # low-confidence rather than crashing the pipeline
    semantic_findings = [
        f for f in report["findings"] if f["rule_id"] in ("no-business-logic-in-controllers", "no-console-log-in-production-code")
    ]
    assert all(f["status"] == "low_confidence_final" for f in semantic_findings)
