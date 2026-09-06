"""Load and validate rule YAML files against the Rule schema."""
from __future__ import annotations

from pathlib import Path

import yaml

from codewarden.rules.schema import RuleSet


def load_ruleset(path: str | Path) -> RuleSet:
    data = yaml.safe_load(Path(path).read_text())
    return RuleSet.model_validate(data)
