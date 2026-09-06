"""Planner role: decides what to check, not whether it's a violation.

Structural rules (import_restriction, layering) are resolved directly
from AST metadata — no LLM call, since these are deterministic checks.
semantic_check rules are resolved via a ChromaDB retrieval query built
from the rule's check_prompt. See DECISIONS.md (Stage 4 entry) for the
full role-boundary rationale.
"""
from __future__ import annotations

from codewarden.agents.models import AnalysisTask
from codewarden.indexing.store import CodeIndex
from codewarden.parsing.model import ParsedFile
from codewarden.rules.matching import scope_matches
from codewarden.rules.schema import Rule, RuleSet

STRUCTURAL_RULE_TYPES = {"import_restriction", "layering"}
RETRY_CONTEXT_SIZE = 8


def _files_in_scope(rule: Rule, parsed_files: dict[str, ParsedFile]) -> list[str]:
    return [
        path
        for path, parsed in parsed_files.items()
        if parsed.language in rule.languages and scope_matches(path, rule.scope.include, rule.scope.exclude)
    ]


def _plan_structural_tasks(rule: Rule, parsed_files: dict[str, ParsedFile]) -> list[AnalysisTask]:
    return [AnalysisTask(rule=rule, file_path=path) for path in _files_in_scope(rule, parsed_files)]


def _plan_semantic_tasks(rule: Rule, parsed_files: dict[str, ParsedFile], index: CodeIndex) -> list[AnalysisTask]:
    in_scope_paths = _files_in_scope(rule, parsed_files)
    if not in_scope_paths:
        return []

    results = index.query(
        rule.params.check_prompt,
        n_results=max(len(in_scope_paths) * 2, 5),
        where={"path": {"$in": in_scope_paths}},
    )
    return [
        AnalysisTask(rule=rule, file_path=r.metadata["path"], chunk_id=r.id, chunk_text=r.text)
        for r in results
        if r.metadata.get("kind") == "function"
    ]


def build_initial_tasks(ruleset: RuleSet, parsed_files: dict[str, ParsedFile], index: CodeIndex) -> list[AnalysisTask]:
    tasks: list[AnalysisTask] = []
    for rule in ruleset.rules:
        if rule.params.rule_type in STRUCTURAL_RULE_TYPES:
            tasks.extend(_plan_structural_tasks(rule, parsed_files))
        elif rule.params.rule_type == "semantic_check":
            tasks.extend(_plan_semantic_tasks(rule, parsed_files, index))
    return tasks


def expand_task_context(task: AnalysisTask, index: CodeIndex) -> AnalysisTask:
    """Re-plan a task the Verifier flagged as ambiguous: widen retrieval."""
    if task.chunk_id is None:
        return task  # structural tasks are never ambiguous; nothing to expand

    results = index.query(
        task.rule.params.check_prompt,
        n_results=RETRY_CONTEXT_SIZE,
        where={"path": task.file_path},
    )
    context = [r.text for r in results if r.id != task.chunk_id]
    return AnalysisTask(
        rule=task.rule,
        file_path=task.file_path,
        chunk_id=task.chunk_id,
        chunk_text=task.chunk_text,
        retrieved_context=context,
        expand_context=True,
    )


def plan(
    ruleset: RuleSet,
    parsed_files: dict[str, ParsedFile],
    index: CodeIndex,
    retry_queue: list[AnalysisTask] | None = None,
) -> list[AnalysisTask]:
    if retry_queue:
        return [expand_task_context(t, index) for t in retry_queue]
    return build_initial_tasks(ruleset, parsed_files, index)
