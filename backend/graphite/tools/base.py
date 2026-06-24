"""Tool primitives: schema, execution context, and the registry.

A ``ToolSchema`` is the LLM-facing description of a tool. ``ToolContext`` bundles
the engines a tool needs. ``ToolRegistry`` stores tools and enforces the
query/mutation split (only ``category == "query"`` tools are exposed to the
agent — ADR-005 / Audit C9).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..errors import GraphiteError, ToolExecutionError, ToolNotFound


@dataclass
class ToolSchema:
    """LLM-facing schema for a tool."""

    name: str
    description: str
    parameters: dict          # JSON Schema for parameters
    returns: str              # human description of the return shape
    category: str             # "query" | "mutation"


@dataclass
class ToolContext:
    """Shared context passed to every tool function."""

    simulation_engine: object
    analysis_engine: object
    twin_manager: object


# A tool callable receives the ToolContext and keyword parameters.
ToolFunc = Callable[..., dict]


class ToolRegistry:
    """Registry of all tools, with query/mutation separation."""

    def __init__(self, context: ToolContext | None = None):
        self._tools: dict[str, ToolFunc] = {}
        self._schemas: dict[str, ToolSchema] = {}
        self._context = context

    def bind(self, context: ToolContext) -> None:
        self._context = context

    def register(self, schema: ToolSchema, func: ToolFunc) -> None:
        if schema.name in self._tools:
            raise ValueError(f"Tool '{schema.name}' already registered")
        self._tools[schema.name] = func
        self._schemas[schema.name] = schema

    def get_tool(self, name: str) -> ToolFunc:
        if name not in self._tools:
            raise ToolNotFound(f"Tool '{name}' not found")
        return self._tools[name]

    def get_schema(self, name: str) -> ToolSchema:
        if name not in self._schemas:
            raise ToolNotFound(f"Tool '{name}' not found")
        return self._schemas[name]

    def list_schemas(self) -> list[ToolSchema]:
        return list(self._schemas.values())

    def list_agent_tools(self) -> list[ToolSchema]:
        """Only query tools are exposed to the agent (ADR-005)."""
        return [s for s in self._schemas.values() if s.category == "query"]

    def execute(self, tool_name: str, parameters: dict | None = None) -> dict:
        """Execute a tool by name with the given parameters.

        Domain errors are converted to structured observations so the agent can
        adapt instead of crashing.
        """
        func = self.get_tool(tool_name)
        params = parameters or {}
        if self._context is None:
            raise ToolExecutionError("ToolRegistry has no bound ToolContext")
        try:
            return func(self._context, **params)
        except GraphiteError as exc:
            return {"error": exc.code, "message": str(exc)}
        except TypeError as exc:
            raise ToolExecutionError(
                f"Invalid parameters for tool '{tool_name}': {exc}"
            ) from exc
