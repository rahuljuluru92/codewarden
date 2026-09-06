"""Pydantic models defining the architectural rule schema.

A rule file is a YAML document containing a list of rules under a top-level
`rules:` key. See rules/examples/*.yaml for real examples and
DECISIONS.md (Stage 1 entry) for the reasoning behind this shape.
"""
from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, Field

Severity = Literal["error", "warning", "info"]
Language = Literal["python", "typescript"]


class Scope(BaseModel):
    """Which files a rule applies to, as glob patterns relative to repo root."""

    include: list[str] = Field(default_factory=lambda: ["**/*"])
    exclude: list[str] = Field(default_factory=list)


class ImportRestrictionParams(BaseModel):
    rule_type: Literal["import_restriction"] = "import_restriction"
    from_module_glob: str
    forbidden_import_globs: list[str]


class LayeringParams(BaseModel):
    rule_type: Literal["layering"] = "layering"
    source_layer_glob: str
    target_layer_glob: str
    direction: Literal["forbidden"] = "forbidden"


class SemanticCheckParams(BaseModel):
    """For rules that aren't reducible to a pure AST/import check and need
    an LLM agent reasoning over retrieved code context (e.g. "controllers
    must not contain business logic")."""

    rule_type: Literal["semantic_check"] = "semantic_check"
    check_prompt: str
    applies_to_glob: str = "**/*"


RuleParams = Union[ImportRestrictionParams, LayeringParams, SemanticCheckParams]


class Rule(BaseModel):
    id: str
    name: str
    description: str
    rationale: str
    severity: Severity = "warning"
    languages: list[Language]
    scope: Scope = Field(default_factory=Scope)
    params: RuleParams = Field(discriminator="rule_type")


class RuleSet(BaseModel):
    rules: list[Rule]
