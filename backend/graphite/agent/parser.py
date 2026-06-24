"""Robust parsing of LLM output into a structured :class:`AgentResponse`.

Gemini is asked for raw JSON, but we defensively handle code fences and leading
or trailing prose so a slightly-malformed response can still be recovered.
"""

from __future__ import annotations

import json
import re

from .schemas import Action, AgentResponse

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class AgentParseError(ValueError):
    """Raised when LLM output cannot be parsed into an AgentResponse."""


def _extract_json_blob(text: str) -> str:
    text = text.strip()
    if not text:
        raise AgentParseError("empty response")

    fence = _FENCE_RE.search(text)
    if fence:
        return fence.group(1).strip()

    # Fall back to the outermost {...} span.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def parse_agent_response(raw: str) -> AgentResponse:
    """Parse raw LLM text into an AgentResponse, or raise AgentParseError."""
    blob = _extract_json_blob(raw)
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise AgentParseError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise AgentParseError("top-level value must be a JSON object")

    thought = data.get("thought", "")
    if not isinstance(thought, str):
        thought = str(thought)

    action = data.get("action")
    if not isinstance(action, dict):
        raise AgentParseError("missing or invalid 'action' object")

    tool = action.get("tool")
    if not isinstance(tool, str) or not tool:
        raise AgentParseError("action.tool must be a non-empty string")

    parameters = action.get("parameters", {})
    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict):
        raise AgentParseError("action.parameters must be an object")

    return AgentResponse(thought=thought, action=Action(tool=tool, parameters=parameters))
