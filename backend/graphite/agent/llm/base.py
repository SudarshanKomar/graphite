"""LLM provider abstraction.

The agent depends only on this protocol, so concrete providers (Gemini, OpenAI,
Anthropic, local, enterprise) are swappable. The ``tools`` parameter is a
generic list (e.g. ``ToolDef`` from the MCP package); providers that need native
tool schemas transform them, otherwise they ignore the param.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..schemas import AgentResponse, Message


@dataclass
class LLMResponse:
    """Raw + parsed result of one LLM completion."""
    raw_text: str
    parsed: AgentResponse | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal interface every LLM backend must implement."""

    async def complete(
        self,
        messages: list[Message],
        tools: list | None = None,
    ) -> LLMResponse:
        ...
