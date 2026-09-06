"""Thin wrapper around the Groq (OpenAI-compatible) chat completions API.

Only the Executor role calls this — Planner and Verifier are deterministic
Python, per the Stage 4 design in DECISIONS.md.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI

DEFAULT_MODEL = "openai/gpt-oss-120b"
# gpt-oss-120b is a reasoning model: it spends tokens on hidden reasoning
# before emitting visible output, so max_tokens must be generous or the
# response comes back empty (verified in DECISIONS.md, Stage 4 entry).
DEFAULT_MAX_TOKENS = 800


@dataclass
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int | None


@dataclass
class LLMResponse:
    content: str
    usage: LLMUsage


def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
    )


def call_llm(prompt: str, client: OpenAI | None = None, model: str | None = None) -> LLMResponse:
    client = client or get_client()
    model = model or os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=DEFAULT_MAX_TOKENS,
    )
    content = response.choices[0].message.content or ""
    details = response.usage.completion_tokens_details if response.usage else None
    usage = LLMUsage(
        prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
        completion_tokens=response.usage.completion_tokens if response.usage else 0,
        reasoning_tokens=getattr(details, "reasoning_tokens", None) if details else None,
    )
    return LLMResponse(content=content, usage=usage)
