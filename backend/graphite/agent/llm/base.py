"""LLM provider abstraction.

The agent depends only on this protocol, so concrete providers (Gemini, OpenAI,
Anthropic, local, enterprise) are swappable. Run 1 ships the interface plus a
Gemini stub; the concrete call path is wired in a later run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..schemas import AgentResponse, Message
from ...tools.base import ToolSchema


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
        tools: list[ToolSchema] | None = None,
    ) -> LLMResponse:
        ...
