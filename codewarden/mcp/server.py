"""MCP server exposing the CodeWarden pipeline as a tool, so it can be
invoked from any MCP-compatible client (Cursor, Windsurf, Claude Desktop).

Run directly (stdio transport, what desktop clients expect):

    python -m codewarden.mcp.server
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from codewarden.agents.graph import run_pipeline
from codewarden.cli.discovery import discover_source_files
from codewarden.indexing.store import CodeIndex
from codewarden.parsing.parser import parse_source
from codewarden.rules.loader import load_ruleset

mcp = MCPServer(
    name="codewarden",
    description="Multi-agent architectural compliance checker: checks a codebase against a rules YAML file using Tree-sitter AST parsing, ChromaDB retrieval, and a LangGraph agent pipeline.",
)


@mcp.tool(
    description="Check a repository against a CodeWarden architectural rules YAML file. Returns a structured JSON report of violations (grouped by severity), or a message if no violations are found."
)
def check_repository(repo_path: str, rules_path: str) -> dict:
    """Run the CodeWarden pipeline against a repo.

    Args:
        repo_path: Absolute or relative path to the directory to check.
        rules_path: Absolute or relative path to a CodeWarden rules YAML file.
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return {"error": f"'{repo_path}' is not a directory."}

    rules_file = Path(rules_path).resolve()
    if not rules_file.is_file():
        return {"error": f"Rules file '{rules_path}' does not exist."}

    ruleset = load_ruleset(rules_file)
    source_files = discover_source_files(repo)
    if not source_files:
        return {"error": f"No supported source files (.py, .ts, .tsx) found under '{repo_path}'."}

    parsed_files = {}
    for path in source_files:
        rel_path = str(path.relative_to(repo))
        parsed_files[rel_path] = parse_source(rel_path, path.read_text(encoding="utf-8"))

    index = CodeIndex(persist_path=tempfile.mkdtemp())
    for parsed in parsed_files.values():
        index.index_parsed_file(parsed)

    return run_pipeline(ruleset, parsed_files, index)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
