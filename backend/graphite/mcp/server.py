"""Graphite MCP Server — the canonical tool/resource interface (ADR-006).

Replaces V1's ``ToolRegistry``. Provides:

* **36 tools** (21 query + 13 mutation + 2 meta) with enriched descriptions
* **7 resources** (overview, 4 per-site, diff) for browsable state
* **Mode enforcement** (ADR-007): mutations refused in observe mode

The ``GraphiteMcpServer`` class is designed for zero-dependency in-process use.
The internal ReAct agent calls its methods directly (no transport overhead).
For external agents, Phase 5 wires the same handlers to MCP SDK stdio transport.
"""

from __future__ import annotations

import json
from typing import Any

from ..errors import GraphiteError
from .mode import CapabilityMode
from .resources import ResourceDef, list_all_resources, read_resource
from .tools import ToolDef, build_tool_defs


class ModeViolation(Exception):
    """Raised when a mutation tool is called in observe mode."""

    def __init__(self, tool_name: str, current_mode: str):
        self.tool_name = tool_name
        self.current_mode = current_mode
        super().__init__(
            f"Tool '{tool_name}' modifies topology state. "
            f"Current mode: {current_mode}. "
            "Switch to operate mode first: "
            "set_capability_mode(mode='operate')"
        )


class GraphiteMcpServer:
    """MCP-compatible server exposing Graphite's digital-twin capabilities.

    For in-process use (internal agent), call methods directly:
    ``list_tools()``, ``call_tool()``, ``list_resources()``, ``read_resource()``.

    For external agents (Phase 5), these same handlers are wired to MCP
    SDK transport (stdio / SSE).
    """

    def __init__(self, analysis_engine, simulation_engine, twin_manager):
        self._analysis = analysis_engine
        self._simulation = simulation_engine
        self._twin = twin_manager
        self._mode = CapabilityMode()

        # Build tool definitions wired to engines.
        self._tool_list: list[ToolDef] = build_tool_defs(
            analysis_engine, simulation_engine, twin_manager, self._mode
        )
        self._tool_map: dict[str, ToolDef] = {t.name: t for t in self._tool_list}

    # -- Mode access ------------------------------------------------------- #

    @property
    def mode(self) -> CapabilityMode:
        return self._mode

    # -- Tool protocol ----------------------------------------------------- #

    def list_tools(self) -> list[ToolDef]:
        """Return all tools. Mutation tools are always listed for
        discoverability; enforcement is in ``call_tool()``.
        """
        return list(self._tool_list)

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        """Execute a tool by name.

        * Unknown tool → ``KeyError``
        * Mode violation → ``ModeViolation``
        * Domain errors → returned as ``{"error": code, "message": text}``
          (agent-friendly observations)
        """
        tool = self._tool_map.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: '{name}'")

        # Mode enforcement (ADR-007): mutations refused in observe mode.
        if tool.category == "mutation" and not self._mode.allows_mutation():
            raise ModeViolation(name, self._mode.current_str)

        args = arguments or {}
        try:
            return tool.handler(**args)
        except GraphiteError as exc:
            # Domain errors become structured observations the agent can adapt to.
            return {"error": exc.code, "message": str(exc)}
        except TypeError as exc:
            return {"error": "InvalidParameters",
                    "message": f"Invalid parameters for '{name}': {exc}"}

    # -- Resource protocol ------------------------------------------------- #

    def list_resources(self) -> list[ResourceDef]:
        return list_all_resources()

    def read_resource(self, uri: str) -> str:
        """Read a resource by URI. Returns JSON string."""
        return read_resource(uri, self._analysis)
