"""Prompt formatting utilities for the ReAct agent."""

from __future__ import annotations

import json


def format_tool_catalog(tools) -> str:
    """Render the available tools as a compact, LLM-readable catalog.

    Accepts objects with ``.name``, ``.description``, and either
    ``.input_schema`` (V2 ``ToolDef``) or ``.parameters`` (V1 ``ToolSchema``).
    """
    lines: list[str] = []
    for schema in sorted(tools, key=lambda s: s.name):
        # Support both V2 ToolDef (input_schema) and V1 ToolSchema (parameters).
        param_spec = getattr(schema, "input_schema", None) or getattr(schema, "parameters", {})
        params = param_spec.get("properties", {})
        required = set(param_spec.get("required", []))
        if params:
            parts = []
            for name, spec in params.items():
                typ = spec.get("type", "any")
                flag = "" if name in required else "?"
                parts.append(f"{name}{flag}: {typ}")
            param_str = ", ".join(parts)
        else:
            param_str = ""
        # ToolDef has no .returns; use description only.
        returns = getattr(schema, "returns", "")
        suffix = f" -> {returns}" if returns else ""
        lines.append(f"- {schema.name}({param_str}){suffix}\n    {schema.description}")
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
