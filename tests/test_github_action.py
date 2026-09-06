from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTION_YML = REPO_ROOT / "action.yml"
WORKFLOW_YML = REPO_ROOT / ".github" / "workflows" / "codewarden-self-check.yml"


def test_action_yml_is_valid_yaml_with_required_fields():
    data = yaml.safe_load(ACTION_YML.read_text())
    assert data["name"] == "CodeWarden"
    assert data["runs"]["using"] == "composite"
    assert len(data["runs"]["steps"]) == 3

    inputs = data["inputs"]
    assert inputs["rules-path"]["required"] is True
    assert inputs["groq-api-key"]["required"] is True
    assert inputs["repo-path"]["default"] == "."
    assert inputs["fail-on"]["default"] == "error"


def test_workflow_yml_uses_local_action_and_secret():
    data = yaml.safe_load(WORKFLOW_YML.read_text())
    steps = data["jobs"]["check-golden-dataset"]["steps"]
    action_step = next(s for s in steps if s.get("uses") == "./")
    assert action_step["with"]["groq-api-key"] == "${{ secrets.GROQ_API_KEY }}"
    assert action_step["with"]["rules-path"] == "rules/examples/example_rules.yaml"
