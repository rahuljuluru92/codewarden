"""Glob matching for rule scopes and import-module targets.

Supports a small, common extension beyond stdlib fnmatch: single-level
`{a,b,c}` brace alternation (e.g. `**/{api,controllers}/**/*`), since the
rule schema's examples (rules/examples/example_rules.yaml) use it and
fnmatch/glob don't support it natively.
"""
from __future__ import annotations

import re
from fnmatch import fnmatch

_BRACE_RE = re.compile(r"\{([^{}]+)\}")


def _expand_braces(pattern: str) -> list[str]:
    match = _BRACE_RE.search(pattern)
    if not match:
        return [pattern]
    prefix, suffix = pattern[: match.start()], pattern[match.end() :]
    options = match.group(1).split(",")
    expanded: list[str] = []
    for option in options:
        expanded.extend(_expand_braces(prefix + option + suffix))
    return expanded


def _normalize(pattern: str) -> str:
    # fnmatch's `*` already matches across `/`, so collapse `**/` and `/**`
    # down to a single `*` rather than leaving redundant wildcards.
    return pattern.replace("**/", "*").replace("/**", "*")


def glob_match(text: str, pattern: str) -> bool:
    return any(fnmatch(text, _normalize(p)) for p in _expand_braces(pattern))


def glob_match_any(text: str, patterns: list[str]) -> bool:
    return any(glob_match(text, p) for p in patterns)


def scope_matches(path: str, include: list[str], exclude: list[str]) -> bool:
    if exclude and glob_match_any(path, exclude):
        return False
    return glob_match_any(path, include)
