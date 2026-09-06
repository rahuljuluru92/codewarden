"""Tree-sitter Language/Parser construction, one per supported language."""
from __future__ import annotations

from functools import lru_cache

import tree_sitter as ts
import tree_sitter_python as tsp
import tree_sitter_typescript as tsts

SUPPORTED_LANGUAGES = {"python", "typescript"}

EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
}


@lru_cache(maxsize=None)
def get_language(language: str) -> ts.Language:
    if language == "python":
        return ts.Language(tsp.language())
    if language == "typescript":
        return ts.Language(tsts.language_typescript())
    raise ValueError(f"Unsupported language: {language}")


def get_parser(language: str) -> ts.Parser:
    return ts.Parser(get_language(language))


def language_for_path(path: str) -> str | None:
    for ext, language in EXTENSION_TO_LANGUAGE.items():
        if path.endswith(ext):
            return language
    return None
