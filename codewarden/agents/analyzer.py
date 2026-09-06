"""Executor/Analyzer role: decides whether one specific task is a violation.

Structural rule types are checked with plain Python against AST-derived
ImportInfo records — no LLM call. semantic_check rule types call the LLM
(the only role in the pipeline that does) and parse a structured verdict.
See DECISIONS.md (Stage 4 entry) for the role-boundary rationale.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from codewarden.agents.llm_client import call_llm
from codewarden.agents.models import AnalysisTask, Finding
from codewarden.parsing.model import ImportInfo, ParsedFile
from codewarden.rules.matching import glob_match

HIGH_CONFIDENCE = 0.75
LOW_CONFIDENCE = 0.4

LLMFn = Callable[[str], str]


def _import_target(imp: ImportInfo, language: str) -> str:
    if not imp.module:
        return ""
    if language == "python":
        return imp.module.replace(".", "/")
    return imp.module  # TypeScript import specifiers are already path-like


def _analyze_import_restriction(task: AnalysisTask, parsed: ParsedFile) -> list[Finding]:
    params = task.rule.params
    findings = []
    for imp in parsed.imports:
        target = _import_target(imp, parsed.language)
        if target and any(glob_match(target, g) for g in params.forbidden_import_globs):
            findings.append(
                Finding(
                    task_key=task.key,
                    rule_id=task.rule.id,
                    severity=task.rule.severity,
                    file_path=task.file_path,
                    start_line=imp.start_line,
                    end_line=imp.end_line,
                    message=f"'{parsed.path}' imports '{imp.raw_text.strip()}', which matches a forbidden import for rule '{task.rule.name}'.",
                    confidence=1.0,
                    status="confirmed",
                    source_task=task,
                )
            )
    return findings


def _analyze_layering(task: AnalysisTask, parsed: ParsedFile) -> list[Finding]:
    params = task.rule.params
    findings = []
    for imp in parsed.imports:
        target = _import_target(imp, parsed.language)
        if target and glob_match(target, params.target_layer_glob):
            findings.append(
                Finding(
                    task_key=task.key,
                    rule_id=task.rule.id,
                    severity=task.rule.severity,
                    file_path=task.file_path,
                    start_line=imp.start_line,
                    end_line=imp.end_line,
                    message=f"'{parsed.path}' (matching source layer '{params.source_layer_glob}') imports '{imp.raw_text.strip()}', which matches the forbidden target layer '{params.target_layer_glob}'.",
                    confidence=1.0,
                    status="confirmed",
                    source_task=task,
                )
            )
    return findings


def _default_llm_fn(prompt: str) -> str:
    return call_llm(prompt).content


def _build_semantic_prompt(task: AnalysisTask) -> str:
    context_block = ""
    if task.retrieved_context:
        joined = "\n\n---\n\n".join(task.retrieved_context)
        context_block = f"\nAdditional related code in this file, for context:\n{joined}\n"

    return f"""You are reviewing code against one architectural rule.

Rule: {task.rule.name}
Rule description: {task.rule.description}
Rationale: {task.rule.rationale}
Check: {task.rule.params.check_prompt}

Code to review:
{task.chunk_text}
{context_block}
Respond with ONLY a JSON object, no other text, in exactly this shape:
{{"violates": true or false, "explanation": "one or two sentences", "confidence": a number between 0.0 and 1.0}}
"""


def _parse_semantic_verdict(raw: str) -> dict | None:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _analyze_semantic_check(task: AnalysisTask, llm_fn: LLMFn) -> list[Finding]:
    prompt = _build_semantic_prompt(task)
    raw = llm_fn(prompt)
    verdict = _parse_semantic_verdict(raw)

    if verdict is None:
        # Can't trust an unparseable response either way — flag as
        # ambiguous rather than silently dropping or falsely confirming.
        return [
            Finding(
                task_key=task.key,
                rule_id=task.rule.id,
                severity=task.rule.severity,
                file_path=task.file_path,
                start_line=0,
                end_line=0,
                message="LLM response could not be parsed as a verdict.",
                confidence=0.5,
                status="ambiguous",
                source_task=task,
            )
        ]

    if not verdict.get("violates"):
        return []

    confidence = float(verdict.get("confidence", 0.5))
    if confidence < LOW_CONFIDENCE:
        return []

    status = "confirmed" if confidence >= HIGH_CONFIDENCE else "ambiguous"
    return [
        Finding(
            task_key=task.key,
            rule_id=task.rule.id,
            severity=task.rule.severity,
            file_path=task.file_path,
            start_line=0,
            end_line=0,
            message=str(verdict.get("explanation", "")),
            confidence=confidence,
            status=status,
            source_task=task,
        )
    ]


def analyze_task(
    task: AnalysisTask,
    parsed_files: dict[str, ParsedFile],
    llm_fn: LLMFn | None = None,
) -> list[Finding]:
    rule_type = task.rule.params.rule_type
    if rule_type == "import_restriction":
        return _analyze_import_restriction(task, parsed_files[task.file_path])
    if rule_type == "layering":
        return _analyze_layering(task, parsed_files[task.file_path])
    if rule_type == "semantic_check":
        return _analyze_semantic_check(task, llm_fn or _default_llm_fn)
    raise ValueError(f"Unknown rule_type: {rule_type}")
