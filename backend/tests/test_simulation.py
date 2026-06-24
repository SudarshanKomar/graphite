"""Tests for the simulation engine: mutations, cascades, service health, reset."""

import pytest

from graphite.errors import (
    DeviceAlreadyDown,
    DeviceDown,
    LinkNotFound,
    VlanAlreadyRemoved,
)


# --- Device disable cascade (Scenario 2) -----------------------------------
def test_disable_leaf_cascades_links(sim, analysis):
    res = sim.disable_device("sg-leaf-03")
    assert res["new_status"] == "down"
    assert "link-sg-leaf03-server03" in res["cascading_effects"]["links_disabled"]
    link = analysis.get_link_info("sg-leaf-03", "sg-server-03")
    assert link["status"] == "down"


def test_disable_leaf_takes_down_db_and_dependents(sim, analysis):
    sim.disable_device("sg-leaf-03")
    assert analysis.graph.get_node("db-cluster")["status"] == "down"
    # auth depends solely on db-cluster -> down (formal rule D4)
    assert analysis.graph.get_node("auth-service")["status"] == "down"
    assert analysis.graph.get_node("erp-service")["status"] == "down"
    # monitoring has no deps and host (sg-server-02) stays up -> healthy
    assert analysis.graph.get_node("monitoring-service")["status"] == "healthy"


def test_disable_already_down_raises(sim):
    sim.disable_device("sg-leaf-03")
    with pytest.raises(DeviceAlreadyDown):
        sim.disable_device("sg-leaf-03")


def test_enable_device_restores(sim, analysis):
    sim.disable_device("sg-leaf-03")
    sim.enable_device("sg-leaf-03")
    assert analysis.graph.get_node("sg-leaf-03")["status"] == "up"
    assert analysis.get_link_info("sg-leaf-03", "sg-server-03")["status"] == "up"
    assert analysis.graph.get_node("db-cluster")["status"] == "healthy"


# --- VLAN removal (Scenario 1) ---------------------------------------------
def test_remove_vlan_disconnects_users(sim):
    res = sim.remove_vlan(420, "bangalore")
    assert res["cascading_effects"]["total_users_affected"] == 5000


def test_remove_vlan_keeps_node_as_removed(sim, analysis):
    sim.remove_vlan(420, "bangalore")
    info = analysis.get_vlan_info(420, "bangalore")
    assert info["status"] == "removed"
    assert info["devices"] == []  # carries_vlan edges removed


def test_remove_vlan_breaks_reachability(sim, analysis):
    sim.remove_vlan(420, "bangalore")
    r = analysis.check_reachability("blr-corp-wifi-users", "erp-service")
    assert r["reachable"] is False


def test_remove_vlan_twice_raises(sim):
    sim.remove_vlan(420, "bangalore")
    with pytest.raises(VlanAlreadyRemoved):
        sim.remove_vlan(420, "bangalore")


def test_add_vlan_restores_connectivity(sim, analysis):
    sim.remove_vlan(420, "bangalore")
    sim.add_vlan(420, "bangalore", "10.42.0.0/16", "Corp WiFi",
                 ["blr-core-01", "blr-core-02", "blr-dist-01", "blr-dist-02",
                  "blr-access-f1", "blr-access-f2", "blr-access-f3", "blr-access-f4"])
    info = analysis.get_vlan_info(420, "bangalore")
    assert info["status"] == "active"
    r = analysis.check_reachability("blr-corp-wifi-users", "erp-service")
    assert r["reachable"] is True


# --- Link latency (Scenario 3) ---------------------------------------------
def test_set_link_latency_changes_trace(sim, analysis):
    sim.set_link_latency("blr-edge-01", "sg-edge-01", 500)
    tr = analysis.trace_route("blr-corp-wifi-users", "erp-service")
    assert tr["total_latency_ms"] > 500
    info = analysis.get_link_info("blr-edge-01", "sg-edge-01")
    assert info["latency_ms"] == 500


def test_disable_link_then_enable(sim, analysis):
    sim.disable_link("blr-edge-01", "sg-edge-01")
    assert analysis.get_link_info("blr-edge-01", "sg-edge-01")["status"] == "down"
    sim.enable_link("blr-edge-01", "sg-edge-01")
    assert analysis.get_link_info("blr-edge-01", "sg-edge-01")["status"] == "up"


def test_enable_link_blocked_when_device_down(sim):
    sim.disable_device("sg-edge-01")
    with pytest.raises(DeviceDown):
        sim.enable_link("blr-edge-01", "sg-edge-01")


def test_link_not_found(sim):
    with pytest.raises(LinkNotFound):
        sim.disable_link("blr-core-01", "sg-server-03")


# --- BGP (reciprocal) ------------------------------------------------------
def test_disable_bgp_peer_is_reciprocal(sim, analysis):
    sim.disable_bgp_peer("blr-edge-01", "10.99.14.2")  # peer = sg-edge-01
    local = analysis.get_device_bgp_summary("blr-edge-01")
    sg = analysis.get_device_bgp_summary("sg-edge-01")
    local_peer = next(p for p in local["peers"] if p["peer_ip"] == "10.99.14.2")
    assert local_peer["state"] == "idle"
    sg_peer = next(p for p in sg["peers"] if p["peer_device"] == "blr-edge-01")
    assert sg_peer["state"] == "idle"


def test_enable_bgp_peer_restores(sim, analysis):
    sim.disable_bgp_peer("blr-edge-01", "10.99.14.2")
    sim.enable_bgp_peer("blr-edge-01", "10.99.14.2")
    local = analysis.get_device_bgp_summary("blr-edge-01")
    local_peer = next(p for p in local["peers"] if p["peer_ip"] == "10.99.14.2")
    assert local_peer["state"] == "established"


# --- Mutation log & comparison ---------------------------------------------
def test_mutation_log_records(sim):
    sim.remove_vlan(420, "bangalore")
    sim.set_link_latency("blr-edge-01", "sg-edge-01", 300)
    log = sim.get_mutation_log()
    assert [r["mutation_type"] for r in log] == ["remove_vlan", "set_link_latency"]


def test_compare_with_baseline_detects_changes(sim, analysis):
    sim.set_link_latency("blr-edge-01", "sg-edge-01", 500)
    diff = analysis.compare_with_baseline()
    types = {c["change_type"] for c in diff["changes"]}
    assert "link_latency" in types


def test_reset_clears_state(sim, analysis):
    sim.remove_vlan(420, "bangalore")
    sim.reset()
    assert analysis.compare_with_baseline()["mutations_applied"] == 0
    assert sim.get_mutation_log() == []
