"""HTTP MCP endpoint — exposes Graphite's MCP server over Streamable HTTP.

Mounts the MCP protocol at ``/mcp`` inside the existing FastAPI application.
External agents (Windsurf, Cascade, Cursor, Claude Desktop) connect via:

    http://127.0.0.1:8000/mcp

The Windsurf MCP config ``url`` should be ``http://127.0.0.1:8000/mcp``.

Design:
- Uses MCP SDK ``StreamableHTTPSessionManager`` (stateless Streamable HTTP transport)
- The ``GraphiteMcpServer`` instance is shared from ``app.state.services``.
- Mutations applied through the MCP endpoint are immediately visible to REST
  endpoints and to the internal ReAct agent.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from mcp.server import Server as MCPLowlevelServer  # type: ignore
from mcp.server.lowlevel.helper_types import ReadResourceContents  # type: ignore
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager  # type: ignore
from mcp.types import Resource, TextContent, Tool  # type: ignore

from starlette.types import Receive, Scope, Send

from ..state import Services
from ...mcp.server import ModeViolation

logger = logging.getLogger(__name__)


def build_mcp_http_components(services: Services) -> tuple[MCPLowlevelServer[Any, Any], StreamableHTTPSessionManager]:
    """Build the lowlevel MCP Server and StreamableHTTPSessionManager.

    Returns:
        (mcp_server, session_manager) — use with _McpMiddleware to intercept /mcp paths
    """
    graphite = services.mcp_server

    server: MCPLowlevelServer[Any, Any] = MCPLowlevelServer("graphite-network-copilot")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        tools = [
            Tool(
                name=t.name,
                description=t.description,
                inputSchema=t.input_schema,
            )
            for t in graphite.list_tools()
        ]
        logger.info(f"[MCP handler] list_tools -> {len(tools)} tools")
        return tools

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None = None) -> list[TextContent]:
        logger.info(f"[MCP handler] call_tool: {name}({arguments})")
        try:
            result = graphite.call_tool(name, arguments)
        except ModeViolation as exc:
            result = {"error": "ModeViolation", "message": str(exc)}
        except KeyError as exc:
            result = {"error": "UnknownTool", "message": str(exc)}
        return [TextContent(type="text", text=json.dumps(result, default=str))]

    @server.list_resources()
    async def handle_list_resources() -> list[Resource]:
        resources = [
            Resource(uri=r.uri, name=r.name, description=r.description)
            for r in graphite.list_resources()
        ]
        logger.info(f"[MCP handler] list_resources -> {len(resources)} resources")
        return resources

    @server.read_resource()
    async def handle_read_resource(uri) -> list[ReadResourceContents]:
        logger.info(f"[MCP handler] read_resource: {uri}")
        text = graphite.read_resource(str(uri))
        return [ReadResourceContents(content=text, mime_type="application/json")]

    # Create StreamableHTTPSessionManager
    session_manager = StreamableHTTPSessionManager(app=server, stateless=True, json_response=True)

    logger.info(f"[MCP] Streamable HTTP transport wired: {len(graphite.list_tools())} tools, "
                f"{len(graphite.list_resources())} resources")

    return server, session_manager


@asynccontextmanager
async def lifespan_mcp_http(session_manager: StreamableHTTPSessionManager):
    """Lifespan context manager for StreamableHTTPSessionManager."""
    async with session_manager.run():
        yield


class _McpMiddleware:
    """Pure ASGI middleware that intercepts /mcp and /mcp/ paths.

    This middleware runs before Starlette routing, avoiding the trailing-slash
    redirect that would occur with a Mount. Preserves raw ASGI (scope, receive, send)
    for StreamableHTTPSessionManager.handle_request.
    """

    def __init__(self, app, session_manager: StreamableHTTPSessionManager):
        self.app = app
        self.session_manager = session_manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")

        if path in ("/mcp", "/mcp/"):
            # Forward request directly to session_manager.handle_request with raw ASGI send
            await self.session_manager.handle_request(scope, receive, send)
            return

        # Pass through all other paths
        await self.app(scope, receive, send)
