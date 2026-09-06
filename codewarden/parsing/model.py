"""Structured representation of a parsed source file.

These are the AST-derived shapes the rule engine actually needs (per the
rule schema in codewarden/rules/schema.py): import statements for
import_restriction/layering rules, and function/class boundaries for
semantic_check rules and later chunking into ChromaDB (Stage 3).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ImportInfo:
    module: str
    names: list[str]
    start_line: int
    end_line: int
    raw_text: str


@dataclass
class FunctionInfo:
    name: str
    start_line: int
    end_line: int
    parent_class: str | None
    source: str


@dataclass
class ClassInfo:
    name: str
    start_line: int
    end_line: int
    method_names: list[str] = field(default_factory=list)


@dataclass
class ParsedFile:
    path: str
    language: str
    source: str
    imports: list[ImportInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
