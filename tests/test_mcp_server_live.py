"""Protocol-level MCP integration test: spawns the real codewarden-mcp
server over stdio (as any MCP client, including Claude Desktop, would)
and calls its tool for real against the Golden Dataset repo, hitting the
real Groq API. Excluded from the default fast suite; run with
`pytest -m live`.
"""
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_REPO = REPO_ROOT / "eval" / "golden_dataset" / "repo"
RULES_PATH = REPO_ROOT / "rules" / "examples" / "example_rules.yaml"


@pytest.mark.live
@pytest.mark.anyio
async def test_mcp_server_lists_and_calls_check_repository_tool():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "codewarden.mcp.server"],
        cwd=str(REPO_ROOT),
        # MCP clients (including Claude Desktop) spawn the server with a
        # minimal environment, not the shell's — GROQ_API_KEY must be
        # passed explicitly, same as a real client config would need to.
        env={**os.environ},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = {t.name for t in tools.tools}
            assert "check_repository" in tool_names

            result = await session.call_tool(
                "check_repository",
                {"repo_path": str(GOLDEN_REPO), "rules_path": str(RULES_PATH)},
            )

            assert not result.is_error
            payload = json.loads(result.content[0].text)
            assert payload["total_findings"] > 0
            rule_ids = {f["rule_id"] for f in payload["findings"]}
            assert "no-controller-db-access" in rule_ids
