"""Standalone MCP server entry point for external agent integration.

Usage::

    python -m graphite.mcp

Boots the digital twin, analysis/simulation engines, and serves the Graphite
MCP tool surface over **stdio** transport. External agents (Claude Desktop,
Windsurf, Cursor, custom MCP clients) connect to this process.

Configuration is minimal — the server uses the same ``network_state/`` JSON
data as the FastAPI backend. No LLM key is needed (the MCP server provides
tools, not an agent).

If the ``mcp`` SDK is not installed, a clear error message is printed.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    # Attempt to import the MCP SDK; give a clear message if missing.
    try:
        from mcp.server.stdio import stdio_server  # type: ignore
    except ImportError:
        print(
            "ERROR: The 'mcp' package is required for stdio transport.\n"
            "Install it with:  pip install mcp\n\n"
            "The in-process MCP server (used by the FastAPI agent) works "
            "without this dependency. The 'mcp' package is only needed for "
            "external agent connections via stdio.",
            file=sys.stderr,
        )
        sys.exit(1)

    import asyncio
    import json

    from mcp.server import Server  # type: ignore
    from mcp.types import TextContent, Tool, Resource  # type: ignore

    from ..analysis import AnalysisEngine
    from ..simulation import SimulationEngine
    from ..twin import TwinBuilder, TwinManager
    from .server import GraphiteMcpServer, ModeViolation

    # --- Boot the twin ---------------------------------------------------- #
    data_dir = Path(__file__).resolve().parent.parent.parent / "network_state"
    if not data_dir.exists():
        print(f"ERROR: network_state directory not found at {data_dir}", file=sys.stderr)
        sys.exit(1)

    tm = TwinManager(TwinBuilder(data_dir))
    tm.initialize()
    tm.clone_working()
    ae = AnalysisEngine(tm)
    se = SimulationEngine(tm)
    graphite = GraphiteMcpServer(ae, se, tm)

    print(f"Graphite MCP: loaded {len(graphite.list_tools())} tools, "
          f"{len(graphite.list_resources())} resources", file=sys.stderr)

    # --- Wire to MCP SDK server ------------------------------------------- #
    server = Server("graphite-network-copilot")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name=t.name,
                description=t.description,
                inputSchema=t.input_schema,
            )
            for t in graphite.list_tools()
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None = None) -> list[TextContent]:
        try:
            result = graphite.call_tool(name, arguments)
        except ModeViolation as exc:
            return [TextContent(type="text", text=json.dumps(
                {"error": "ModeViolation", "message": str(exc)}
            ))]
        except KeyError as exc:
            return [TextContent(type="text", text=json.dumps(
                {"error": "UnknownTool", "message": str(exc)}
            ))]
        return [TextContent(type="text", text=json.dumps(result, default=str))]

    @server.list_resources()
    async def handle_list_resources() -> list[Resource]:
        return [
            Resource(uri=r.uri, name=r.name, description=r.description)
            for r in graphite.list_resources()
        ]

    @server.read_resource()
    async def handle_read_resource(uri: str) -> str:
        return graphite.read_resource(uri)

    # --- Run on stdio ----------------------------------------------------- #
    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
