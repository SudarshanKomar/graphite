"""Graphite MCP server — the canonical tool interface for V2.

Replaces V1's custom ToolRegistry (ADR-006). The ``GraphiteMcpServer`` class
exposes all analysis/simulation capabilities as MCP-compatible tools with
mode-based access control (ADR-007: observe / operate).
"""

from .mode import CapabilityMode
from .server import GraphiteMcpServer

__all__ = ["CapabilityMode", "GraphiteMcpServer"]
