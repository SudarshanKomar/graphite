"""Tests for the tool registry and query/mutation split."""

import pytest

from graphite.errors import ToolNotFound


def test_registry_has_all_34_tools(registry):
    assert len(registry.list_schemas()) == 34


def test_agent_sees_only_21_query_tools(registry):
    agent_tools = registry.list_agent_tools()
    assert len(agent_tools) == 21
    assert all(s.category == "query" for s in agent_tools)


def test_no_mutation_tool_exposed_to_agent(registry):
    names = {s.name for s in registry.list_agent_tools()}
    for forbidden in ("disable_device", "remove_vlan", "set_link_latency",
                      "disable_bgp_peer"):
        assert forbidden not in names


def test_execute_query_tool(registry):
    result = registry.execute("get_device_info", {"device_id": "blr-core-01"})
    assert result["id"] == "blr-core-01"
    assert result["device_type"] == "core_switch"


def test_execute_blast_radius_through_registry(registry):
    result = registry.execute("get_blast_radius", {"component_id": "blr-vlan-420"})
    assert result["severity"] == "critical"


def test_execute_mutation_tool_changes_state(registry, analysis):
    result = registry.execute("remove_vlan", {"vlan_id": 420, "site": "bangalore"})
    assert result["cascading_effects"]["total_users_affected"] == 5000
    assert analysis.get_vlan_info(420, "bangalore")["status"] == "removed"


def test_execute_unknown_tool_raises(registry):
    with pytest.raises(ToolNotFound):
        registry.execute("teleport_device", {})


def test_domain_error_returned_as_observation(registry):
    # Unknown device should surface as a structured error, not an exception.
    result = registry.execute("get_device_info", {"device_id": "ghost"})
    assert result["error"] == "DeviceNotFound"


def test_compare_with_baseline_tool_no_params(registry):
    result = registry.execute("compare_with_baseline", {})
    assert result["mutations_applied"] == 0
