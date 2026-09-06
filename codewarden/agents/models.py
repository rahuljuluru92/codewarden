"""Shared data shapes passed between the Planner, Executor, and Verifier."""
from __future__ import annotations

from dataclasses import dataclass, field

from codewarden.rules.schema import Rule


@dataclass
class AnalysisTask:
    rule: Rule
    file_path: str
    chunk_id: str | None = None
    chunk_text: str | None = None
    retrieved_context: list[str] = field(default_factory=list)
    expand_context: bool = False

    @property
    def key(self) -> str:
        return f"{self.rule.id}:{self.file_path}:{self.chunk_id or ''}"


@dataclass
class Finding:
    task_key: str
    rule_id: str
    severity: str
    file_path: str
    start_line: int
    end_line: int
    message: str
    confidence: float
    status: str  # "confirmed" | "ambiguous" | "low_confidence_final"
    source_task: AnalysisTask
