"""Tests for the MCP server: tool surface, mode enforcement, resources (V2)."""

import json

import pytest

from graphite.mcp.server import ModeViolation


# --- Tool inventory -------------------------------------------------------

def test_mcp_server_has_36_tools(mcp_server):
    assert len(mcp_server.list_tools()) == 36


def test_tool_categories(mcp_server):
    tools = mcp_server.list_tools()
    cats = {}
    for t in tools:
        cats.setdefault(t.category, []).append(t.name)
    assert len(cats["query"]) == 21
    assert len(cats["mutation"]) == 13
    assert len(cats["meta"]) == 2


def test_mutation_tools_include_destructive_and_restorative(mcp_server):
    mutation_names = {t.name for t in mcp_server.list_tools() if t.category == "mutation"}
    assert "disable_device" in mutation_names  # destructive
    assert "enable_device" in mutation_names   # restorative
    assert "remove_vlan" in mutation_names     # destructive
    assert "add_vlan" in mutation_names        # restorative


# --- Mode enforcement (ADR-007) -------------------------------------------

def test_default_mode_is_observe(mcp_server):
    assert mcp_server.mode.current_str == "observe"


def test_mutation_refused_in_observe(mcp_server):
    with pytest.raises(ModeViolation):
        mcp_server.call_tool("disable_device", {"device_id": "blr-core-01"})


def test_query_allowed_in_observe(mcp_server):
    result = mcp_server.call_tool("get_device_info", {"device_id": "blr-core-01"})
    assert result["id"] == "blr-core-01"


def test_switch_to_operate_enables_mutation(mcp_server):
    mcp_server.call_tool("set_capability_mode", {"mode": "operate"})
    assert mcp_server.mode.current_str == "operate"
    result = mcp_server.call_tool("disable_device", {"device_id": "blr-core-01"})
    assert result["new_status"] == "down"


def test_switch_back_to_observe_blocks_mutation(mcp_server):
    mcp_server.call_tool("set_capability_mode", {"mode": "operate"})
    mcp_server.call_tool("set_capability_mode", {"mode": "observe"})
    with pytest.raises(ModeViolation):
        mcp_server.call_tool("disable_device", {"device_id": "blr-core-01"})


# --- Query tool execution -------------------------------------------------

def test_execute_query_tool(mcp_server):
    result = mcp_server.call_tool("get_device_info", {"device_id": "blr-core-01"})
    assert result["device_type"] == "core_switch"


def test_blast_radius_via_mcp(mcp_server):
    result = mcp_server.call_tool("get_blast_radius", {"component_id": "blr-vlan-420"})
    assert result["severity"] == "critical"


# --- Mutation tool execution -----------------------------------------------

def test_mutation_tool_changes_state(mcp_server, analysis):
    mcp_server.call_tool("set_capability_mode", {"mode": "operate"})
    result = mcp_server.call_tool("remove_vlan", {"vlan_id": 420, "site": "bangalore"})
    assert result["cascading_effects"]["total_users_affected"] == 5000
    assert analysis.get_vlan_info(420, "bangalore")["status"] == "removed"


# --- Meta-tools ------------------------------------------------------------

def test_reset_simulation(mcp_server, analysis):
    mcp_server.call_tool("set_capability_mode", {"mode": "operate"})
    mcp_server.call_tool("disable_device", {"device_id": "blr-core-01"})
    result = mcp_server.call_tool("reset_simulation")
    assert result["mutations_cleared"] >= 1
    # After reset, device should be up again
    info = mcp_server.call_tool("get_device_info", {"device_id": "blr-core-01"})
    assert info["status"] == "up"


# --- Domain errors as observations -----------------------------------------

def test_domain_error_returns_structured_observation(mcp_server):
    result = mcp_server.call_tool("get_device_info", {"device_id": "nonexistent-device"})
    assert "error" in result
    assert result["error"] == "DeviceNotFound"


# --- Unknown tool ----------------------------------------------------------

def test_unknown_tool_raises_key_error(mcp_server):
    with pytest.raises(KeyError):
        mcp_server.call_tool("nonexistent_tool", {})


# --- Resources -------------------------------------------------------------

def test_list_resources(mcp_server):
    resources = mcp_server.list_resources()
    assert len(resources) == 6  # overview + 4 sites + diff
    uris = {r.uri for r in resources}
    assert "graphite://topology/overview" in uris
    assert "graphite://state/diff" in uris
    assert "graphite://topology/sites/bangalore" in uris


def test_read_resource_overview(mcp_server):
    data = json.loads(mcp_server.read_resource("graphite://topology/overview"))
    assert "sites" in data
    assert len(data["sites"]) == 4


def test_read_resource_site(mcp_server):
    data = json.loads(mcp_server.read_resource("graphite://topology/sites/singapore"))
    assert data["site"] == "singapore"


def test_read_resource_diff(mcp_server):
    data = json.loads(mcp_server.read_resource("graphite://state/diff"))
    assert isinstance(data, dict)
