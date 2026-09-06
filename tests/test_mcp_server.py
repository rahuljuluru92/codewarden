from pathlib import Path

from codewarden.mcp.server import check_repository, mcp

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "examples" / "example_rules.yaml"


def test_check_repository_registered_as_tool():
    import anyio

    tools = anyio.run(mcp.list_tools)
    assert any(t.name == "check_repository" for t in tools)


def test_check_repository_rejects_nonexistent_repo_path(tmp_path):
    result = check_repository(str(tmp_path / "does-not-exist"), str(RULES_PATH))
    assert "error" in result


def test_check_repository_rejects_nonexistent_rules_path(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    result = check_repository(str(tmp_path), str(tmp_path / "no-rules.yaml"))
    assert "error" in result


def test_check_repository_rejects_empty_repo(tmp_path):
    result = check_repository(str(tmp_path), str(RULES_PATH))
    assert "error" in result
