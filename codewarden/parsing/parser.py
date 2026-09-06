"""Top-level entry point: parse a source file into a ParsedFile."""
from __future__ import annotations

from pathlib import Path

from codewarden.parsing.extractors import extract_python, extract_typescript
from codewarden.parsing.languages import get_parser, language_for_path
from codewarden.parsing.model import ParsedFile


def parse_source(path: str, source: str) -> ParsedFile:
    language = language_for_path(path)
    if language is None:
        raise ValueError(f"Unsupported file extension for path: {path}")

    source_bytes = source.encode("utf-8")
    tree = get_parser(language).parse(source_bytes)

    if language == "python":
        imports, functions, classes = extract_python(tree.root_node, source_bytes)
    elif language == "typescript":
        imports, functions, classes = extract_typescript(tree.root_node, source_bytes)
    else:  # pragma: no cover - guarded by language_for_path
        raise ValueError(f"Unsupported language: {language}")

    return ParsedFile(
        path=path,
        language=language,
        source=source,
        imports=imports,
        functions=functions,
        classes=classes,
    )


def parse_file(path: str | Path) -> ParsedFile:
    path = Path(path)
    return parse_source(str(path), path.read_text(encoding="utf-8"))
