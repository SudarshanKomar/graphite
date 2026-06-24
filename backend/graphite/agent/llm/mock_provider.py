"""Deterministic mock LLM provider for tests and offline demos.

Implements the :class:`LLMProvider` protocol without any network calls. Supply
either a fixed list of responses (consumed in order) or a ``handler`` callable
that computes the next response from the current message list.
"""

from __future__ import annotations

import json
from typing import Callable

from ..schemas import Message
from ...tools.base import ToolSchema
from .base import LLMResponse

# A response may be a raw JSON string or a dict (serialised automatically).
Response = str | dict
Handler = Callable[[list[Message], "list[ToolSchema] | None"], Response]


class MockProvider:
    """Scripted LLMProvider for deterministic agent tests."""

    def __init__(self, responses: list[Response] | None = None,
                 handler: Handler | None = None):
        if responses is None and handler is None:
            raise ValueError("MockProvider needs either `responses` or `handler`")
        self._responses = list(responses or [])
        self._handler = handler
        self.calls: list[list[Message]] = []

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
    ) -> LLMResponse:
        self.calls.append(list(messages))
        if self._handler is not None:
            raw = self._handler(messages, tools)
        elif self._responses:
            raw = self._responses.pop(0)
        else:
            raise RuntimeError("MockProvider ran out of scripted responses")
        text = raw if isinstance(raw, str) else json.dumps(raw)
        return LLMResponse(raw_text=text)
