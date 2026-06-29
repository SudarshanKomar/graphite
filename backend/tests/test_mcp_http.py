"""Tests for the HTTP MCP endpoint at /mcp.

Each test calls ``mcp_post()`` which drives a complete MCP request/response
cycle inside a fresh ``anyio.run()`` context.  This sidesteps the
pytest-asyncio loop-scope mismatch that arises when an async generator
fixture holding an anyio task group (``session_manager.run()``) is combined
with function-scoped test event loops.
"""

from __future__ import annotations

import json

import anyio
import httpx
import pytest

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from graphite.api.routes.mcp_http import build_mcp_http_components
from graphite.api.state import build_services
from graphite.config import Settings


def _settings():
    return Settings(gemini_api_key="")


def _first_result(body: str) -> dict:
    """Parse the JSON-RPC response body (json_response=True mode returns plain JSON)."""
    return json.loads(body)


MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def mcp_post(mcp_lowlevel_server, payload: dict) -> httpx.Response:
    """Run a single MCP request synchronously inside its own anyio event loop.

    Creates a fresh ``StreamableHTTPSessionManager`` per call because
    ``run()`` can only be called once per instance.  The shared state lives
    in ``mcp_lowlevel_server`` (and the ``GraphiteMcpServer`` it delegates
    to), so a fresh manager wrapper does not lose any application state.
    """
    async def _run() -> httpx.Response:
        mgr = StreamableHTTPSessionManager(app=mcp_lowlevel_server, stateless=True, json_response=True)
        
        # Create ASGI handler that calls session_manager.handle_request
        async def asgi_handler(scope, receive, send):
            await mgr.handle_request(scope, receive, send)
        
        async with mgr.run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=asgi_handler),
                base_url="http://testserver",
            ) as client:
                return await client.post("/", headers=MCP_HEADERS, json=payload)

    return anyio.run(_run)


@pytest.fixture(scope="module")
def mcp_components():
    """Build MCP lowlevel server + services once per module.

    The lowlevel Server holds the handler registrations; the GraphiteMcpServer
    (inside services) holds the actual tool/resource/simulation state.
    A fresh StreamableHTTPSessionManager is created per request in mcp_post.
    """
    services = build_services(_settings())
    mcp_lowlevel_server, _ = build_mcp_http_components(services)
    return mcp_lowlevel_server, services


def _post(mcp_components, payload: dict) -> httpx.Response:
    mcp_lowlevel_server, _ = mcp_components
    return mcp_post(mcp_lowlevel_server, payload)


def test_mcp_initialize(mcp_components):
    """MCP initialize handshake returns 200 with server info."""
    r = _post(mcp_components, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1.0"},
        },
    })
    assert r.status_code == 200
    result = _first_result(r.text)
    assert result["jsonrpc"] == "2.0"
    assert "protocolVersion" in result["result"]
    assert result["result"]["serverInfo"]["name"] == "graphite-network-copilot"


def test_mcp_tools_list_returns_36_tools(mcp_components):
    """tools/list must return exactly 36 tools."""
    r = _post(mcp_components, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    assert r.status_code == 200
    result = _first_result(r.text)
    tools = result["result"]["tools"]
    names = {t["name"] for t in tools}
    assert len(names) == 36
    assert "get_device_info" in names
    assert "disable_device" in names
    assert "set_capability_mode" in names
    assert "get_site_topology" in names


def test_mcp_resources_list(mcp_components):
    """resources/list must include the topology overview resource."""
    r = _post(mcp_components, {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}})
    assert r.status_code == 200
    result = _first_result(r.text)
    uris = {res["uri"] for res in result["result"]["resources"]}
    assert "graphite://topology/overview" in uris


def test_mcp_tool_call_get_blast_radius(mcp_components):
    """tools/call get_blast_radius returns correct blast-radius data."""
    r = _post(mcp_components, {
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "get_blast_radius", "arguments": {"component_id": "blr-vlan-420"}},
    })
    assert r.status_code == 200
    result = _first_result(r.text)
    text = json.loads(result["result"]["content"][0]["text"])
    assert text["total_users_affected"] == 5000
    assert text["severity"] == "critical"


def test_mcp_mode_violation_returns_error_payload(mcp_components):
    """Mutation tool in observe mode returns ModeViolation error, not HTTP 500."""
    r = _post(mcp_components, {
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "disable_device", "arguments": {"device_id": "blr-core-01"}},
    })
    assert r.status_code == 200
    result = _first_result(r.text)
    payload = json.loads(result["result"]["content"][0]["text"])
    assert payload["error"] == "ModeViolation"


def test_mcp_state_consistency_shared_twin_manager(mcp_components):
    """Mutation via MCP is immediately visible through the shared TwinManager.

    Validates the single-source-of-truth constraint: the HTTP MCP endpoint and
    the analysis engine share the same TwinManager — no duplicate state.
    """
    mcp_lowlevel_server, services = mcp_components
    analysis = services.analysis

    def post(payload):
        return mcp_post(mcp_lowlevel_server, payload)

    # Switch to operate mode
    r = post({"jsonrpc": "2.0", "id": 10, "method": "tools/call",
              "params": {"name": "set_capability_mode", "arguments": {"mode": "operate"}}})
    assert r.status_code == 200

    # Verify device is up before mutation
    assert analysis.get_device_info("blr-core-01")["status"] == "up"

    # Disable via MCP
    r = post({"jsonrpc": "2.0", "id": 11, "method": "tools/call",
              "params": {"name": "disable_device", "arguments": {"device_id": "blr-core-01"}}})
    assert r.status_code == 200

    # Mutation must be visible through the shared AnalysisEngine
    assert analysis.get_device_info("blr-core-01")["status"] == "down"

    # Reset and verify recovery
    r = post({"jsonrpc": "2.0", "id": 12, "method": "tools/call",
              "params": {"name": "reset_simulation", "arguments": {}}})
    assert r.status_code == 200
    assert analysis.get_device_info("blr-core-01")["status"] == "up"
