"""Find source files under a target repo, skipping the usual noise dirs."""
from __future__ import annotations

from pathlib import Path

SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "chroma_db",
    ".pytest_cache",
    ".mypy_cache",
}
SUPPORTED_SUFFIXES = {".py", ".ts", ".tsx"}


def discover_source_files(repo_path: Path) -> list[Path]:
    files = []
    for path in repo_path.rglob("*"):
        if not path.is_file() or path.suffix not in SUPPORTED_SUFFIXES:
            continue
        if any(part in SKIP_DIR_NAMES or part.startswith(".") for part in path.relative_to(repo_path).parts[:-1]):
            continue
        files.append(path)
    return sorted(files)
