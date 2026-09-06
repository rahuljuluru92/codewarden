"""Planner -> Executor -> Verifier DAG, with a retry loop back to Planner
when the Verifier flags ambiguous findings. See DECISIONS.md (Stage 4
entry) for the design rationale.
"""
from __future__ import annotations

from typing import Any, Callable, TypedDict

from langgraph.graph import END, StateGraph

from codewarden.agents.analyzer import analyze_task
from codewarden.agents.models import AnalysisTask, Finding
from codewarden.agents.planner import plan
from codewarden.agents.verifier import DEFAULT_MAX_ITERATIONS, build_report, verify
from codewarden.indexing.store import CodeIndex
from codewarden.parsing.model import ParsedFile
from codewarden.rules.schema import RuleSet


class PipelineState(TypedDict, total=False):
    ruleset: RuleSet
    parsed_files: dict[str, ParsedFile]
    index: CodeIndex
    llm_fn: Callable[[str], str] | None
    max_iterations: int
    tasks: list[AnalysisTask]
    retry_queue: list[AnalysisTask]
    retried_task_keys: set[str]
    findings: list[Finding]
    iteration: int
    report: dict[str, Any] | None


def plan_node(state: PipelineState) -> dict:
    tasks = plan(state["ruleset"], state["parsed_files"], state["index"], retry_queue=state.get("retry_queue"))
    return {"tasks": tasks, "retry_queue": []}


def execute_node(state: PipelineState) -> dict:
    new_findings: list[Finding] = []
    for task in state.get("tasks", []):
        new_findings.extend(analyze_task(task, state["parsed_files"], llm_fn=state.get("llm_fn")))
    return {"findings": state.get("findings", []) + new_findings, "tasks": []}


def verify_node(state: PipelineState) -> dict:
    iteration = state.get("iteration", 0) + 1
    max_iterations = state.get("max_iterations", DEFAULT_MAX_ITERATIONS)
    kept, retry_tasks, retried_keys = verify(
        state.get("findings", []),
        iteration,
        max_iterations,
        state.get("retried_task_keys"),
    )
    report = None if retry_tasks else build_report(kept)
    return {
        "findings": kept,
        "retry_queue": retry_tasks,
        "retried_task_keys": retried_keys,
        "iteration": iteration,
        "report": report,
    }


def _route_after_verify(state: PipelineState) -> str:
    return "plan" if state.get("retry_queue") else "end"


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("verify", verify_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "verify")
    graph.add_conditional_edges("verify", _route_after_verify, {"plan": "plan", "end": END})

    return graph.compile()


def run_pipeline(
    ruleset: RuleSet,
    parsed_files: dict[str, ParsedFile],
    index: CodeIndex,
    llm_fn: Callable[[str], str] | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> dict:
    app = build_graph()
    result = app.invoke(
        {
            "ruleset": ruleset,
            "parsed_files": parsed_files,
            "index": index,
            "llm_fn": llm_fn,
            "max_iterations": max_iterations,
            "findings": [],
            "iteration": 0,
        }
    )
    return result["report"]
