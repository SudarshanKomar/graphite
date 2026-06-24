"""Prompt formatting utilities for the ReAct agent."""

from __future__ import annotations

import json

from ...tools.base import ToolSchema


def format_tool_catalog(tools: list[ToolSchema]) -> str:
    """Render the available tools as a compact, LLM-readable catalog."""
    lines: list[str] = []
    for schema in sorted(tools, key=lambda s: s.name):
        params = schema.parameters.get("properties", {})
        required = set(schema.parameters.get("required", []))
        if params:
            parts = []
            for name, spec in params.items():
                typ = spec.get("type", "any")
                flag = "" if name in required else "?"
                parts.append(f"{name}{flag}: {typ}")
            param_str = ", ".join(parts)
        else:
            param_str = ""
        lines.append(f"- {schema.name}({param_str}) -> {schema.returns}\n    {schema.description}")
    return "\n".join(lines)


def format_observation(tool_name: str, result: dict) -> str:
    """Format a tool result as the observation message for the next turn."""
    body = json.dumps(result, indent=2, default=str)
    return f"Observation from {tool_name}:\n{body}"


def format_parse_retry(raw_text: str, error: str) -> str:
    """Corrective feedback when the model returns malformed output."""
    return (
        "Your previous response could not be parsed as valid JSON.\n"
        f"Parse error: {error}\n\n"
        "Respond again with ONLY a single JSON object matching the required "
        "format: an object with keys \"thought\" (string) and \"action\" "
        "(object with \"tool\" and \"parameters\"). Do not include any prose, "
        "markdown, or code fences outside the JSON."
    )


def format_max_iterations_notice(max_iterations: int) -> str:
    return (
        f"You have reached the maximum of {max_iterations} investigation steps. "
        "Stop calling tools now and respond with a final_answer action that "
        "summarises your findings so far, clearly noting that the investigation "
        "was truncated and confidence is therefore reduced."
    )
