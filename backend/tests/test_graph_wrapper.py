"""Tests for GraphWrapper typed accessors."""

import pytest

from graphite.errors import NodeNotFound


def test_get_node_returns_copy_with_id(analysis):
    g = analysis.graph
    node = g.get_node("blr-core-01")
    assert node["id"] == "blr-core-01"
    node["status"] = "down"  # mutating the copy must not affect the graph
    assert g.get_node("blr-core-01")["status"] == "up"


def test_get_node_missing_raises(analysis):
    with pytest.raises(NodeNotFound):
        analysis.graph.get_node("does-not-exist")


def test_get_devices_filters(analysis):
    g = analysis.graph
    cores = g.get_devices(device_type="core_switch")
    assert {d["id"] for d in cores} >= {"blr-core-01", "blr-core-02"}
    blr = g.get_devices(site="bangalore")
    assert all(d["site"] == "bangalore" for d in blr)


def test_physical_neighbors_and_status_filter(analysis):
    g = analysis.graph
    neighbors = set(g.get_physical_neighbors("blr-core-01"))
    assert "blr-dist-01" in neighbors
    assert "blr-core-02" in neighbors


def test_vlan_devices_and_user_groups(analysis):
    g = analysis.graph
    devices = g.get_vlan_devices("blr-vlan-420")
    assert "blr-core-01" in devices
    groups = g.get_vlan_user_groups("blr-vlan-420")
    assert any(grp["id"] == "blr-corp-wifi-users" for grp in groups)


def test_service_deps_and_dependents(analysis):
    g = analysis.graph
    assert set(g.get_service_deps("erp-service")) == {"auth-service", "db-cluster"}
    assert "erp-service" in g.get_service_dependents("db-cluster")


def test_find_edge_by_link_id(analysis):
    g = analysis.graph
    edge = g.find_edge_by_link_id("link-blr-sg-wan")
    assert edge is not None
    src, dst, data = edge
    assert {src, dst} == {"blr-edge-01", "sg-edge-01"}


def test_neighbors_direction(analysis):
    g = analysis.graph
    # belongs_to points device -> site, so site is an out-neighbor of device.
    out = g.get_neighbors("blr-core-01", relation="belongs_to", direction="out")
    assert "site-bangalore" in out
    # And device is an in-neighbor of the site.
    incoming = g.get_neighbors("site-bangalore", relation="belongs_to", direction="in")
    assert "blr-core-01" in incoming
