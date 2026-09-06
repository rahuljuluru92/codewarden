"""Turn a Stage 2 ParsedFile into AST-derived chunks for ChromaDB.

Chunks are built from the structured function/class boundaries produced
by codewarden/parsing, not from naive fixed-size text splitting — each
chunk is one whole function or one class summary, so retrieval returns
semantically complete units.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from codewarden.parsing.model import ParsedFile


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


def _function_chunk(parsed: ParsedFile, fn) -> Chunk:
    header = f"File: {parsed.path}\n"
    if fn.parent_class:
        header += f"Class: {fn.parent_class}\n"
    header += f"Function: {fn.name}\n\n"
    return Chunk(
        id=f"{parsed.path}::function::{fn.parent_class or ''}::{fn.name}::{fn.start_line}",
        text=header + fn.source,
        metadata={
            "path": parsed.path,
            "language": parsed.language,
            "kind": "function",
            "name": fn.name,
            "parent_class": fn.parent_class or "",
            "start_line": fn.start_line,
            "end_line": fn.end_line,
        },
    )


def _class_chunk(parsed: ParsedFile, cls) -> Chunk:
    methods = ", ".join(cls.method_names) if cls.method_names else "(no methods)"
    text = f"File: {parsed.path}\nClass: {cls.name}\nMethods: {methods}\n"
    return Chunk(
        id=f"{parsed.path}::class::{cls.name}::{cls.start_line}",
        text=text,
        metadata={
            "path": parsed.path,
            "language": parsed.language,
            "kind": "class",
            "name": cls.name,
            "parent_class": "",
            "start_line": cls.start_line,
            "end_line": cls.end_line,
        },
    )


def chunk_parsed_file(parsed: ParsedFile) -> list[Chunk]:
    chunks = [_function_chunk(parsed, fn) for fn in parsed.functions]
    chunks += [_class_chunk(parsed, cls) for cls in parsed.classes]
    return chunks
