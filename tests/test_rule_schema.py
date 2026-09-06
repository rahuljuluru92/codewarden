from pathlib import Path

import pytest
from pydantic import ValidationError

from codewarden.rules.loader import load_ruleset
from codewarden.rules.schema import Rule, RuleSet

EXAMPLES_PATH = Path(__file__).resolve().parent.parent / "rules" / "examples" / "example_rules.yaml"


def test_example_rules_file_loads_and_validates():
    ruleset = load_ruleset(EXAMPLES_PATH)
    assert isinstance(ruleset, RuleSet)
    assert len(ruleset.rules) == 4
    assert {r.id for r in ruleset.rules} == {
        "no-controller-db-access",
        "no-service-to-api-import",
        "no-console-log-in-production-code",
        "no-business-logic-in-controllers",
    }


def test_each_rule_type_is_represented():
    ruleset = load_ruleset(EXAMPLES_PATH)
    rule_types = {r.params.rule_type for r in ruleset.rules}
    assert rule_types == {"import_restriction", "layering", "semantic_check"}


def test_rule_rejects_unknown_rule_type():
    with pytest.raises(ValidationError):
        Rule.model_validate(
            {
                "id": "bad-rule",
                "name": "Bad",
                "description": "x",
                "rationale": "x",
                "languages": ["python"],
                "params": {"rule_type": "not_a_real_type"},
            }
        )


def test_scope_defaults_to_match_everything():
    ruleset = load_ruleset(EXAMPLES_PATH)
    layering_rule = next(r for r in ruleset.rules if r.id == "no-service-to-api-import")
    assert layering_rule.scope.include == ["**/services/**/*"]
    assert layering_rule.scope.exclude == []
