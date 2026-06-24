"""Tests for the analysis engine (pure queries)."""

import pytest

from graphite.errors import ComponentNotFound, DeviceNotFound, SiteNotFound


# --- Path ------------------------------------------------------------------
def test_trace_route_wifi_to_erp(analysis):
    tr = analysis.trace_route("blr-corp-wifi-users", "erp-service")
    assert tr["reachable"] is True
    path = [h["device_id"] for h in tr["hops"]]
    assert path[0] == "blr-access-f1"
    assert path[-1] == "sg-server-01"
    assert "blr-edge-01" in path and "sg-edge-01" in path
    assert tr["total_latency_ms"] == pytest.approx(56.2, abs=0.5)


def test_check_reachability_true(analysis):
    r = analysis.check_reachability("blr-corp-wifi-users", "erp-service")
    assert r["reachable"] is True
    assert r["path"][0] == "blr-access-f1"


def test_alternative_paths_have_multiple_routes(analysis):
    alt = analysis.get_alternative_paths("blr-edge-01", "sg-edge-01")
    assert alt["total_paths"] >= 2
    # Direct link should be the lowest-latency active path.
    assert alt["paths"][0]["path"] == ["blr-edge-01", "sg-edge-01"]
    assert alt["paths"][0]["is_active"] is True


# --- Blast radius ----------------------------------------------------------
def test_blast_radius_vlan420_is_critical(analysis):
    br = analysis.get_blast_radius("blr-vlan-420")
    assert br["total_users_affected"] == 5000
    assert br["severity"] == "critical"
    assert any(g["id"] == "blr-corp-wifi-users" for g in br["affected_user_groups"])


def test_blast_radius_unknown_component_raises(analysis):
    with pytest.raises(ComponentNotFound):
        analysis.get_blast_radius("nope-123")


def test_blast_radius_link_resolves_by_id(analysis):
    br = analysis.get_blast_radius("link-blr-sg-wan")
    assert br["component_type"] == "link"
    assert {d["id"] for d in br["affected_devices"]} == {"blr-edge-01", "sg-edge-01"}


def test_service_dependencies_transitive(analysis):
    dep = analysis.get_service_dependencies("erp-service")
    direct = {d["id"] for d in dep["direct_dependencies"]}
    assert direct == {"auth-service", "db-cluster"}
    # db-cluster reached transitively through auth-service as well.
    assert dep["host_device"] == "sg-server-01"


# --- Redundancy ------------------------------------------------------------
def test_single_homed_server_is_spof(analysis):
    spof = analysis.get_single_points_of_failure("singapore")
    ids = {s["component_id"] for s in spof["single_points_of_failure"]}
    assert "sg-leaf-03" in ids


def test_redundancy_status_leaf_is_spof(analysis):
    red = analysis.get_redundancy_status("sg-leaf-03")
    assert red["has_redundancy"] is False
    assert red["risk_assessment"] == "single_point_of_failure"


def test_failover_path_for_wan_link(analysis):
    fo = analysis.get_failover_path("link-blr-sg-wan")
    assert fo["failover_available"] is True
    assert fo["failover_path"][0] == "blr-edge-01"
    assert fo["failover_path"][-1] == "sg-edge-01"


# --- Topology --------------------------------------------------------------
def test_site_summary_healthy_baseline(analysis):
    s = analysis.get_site_summary("bangalore")
    assert s["health"] == "healthy"
    assert s["devices_down"] == 0


def test_site_topology_contains_devices(analysis):
    topo = analysis.get_site_topology("singapore")
    ids = {d["id"] for d in topo["devices"]}
    assert {"sg-leaf-03", "sg-server-03"} <= ids


def test_inter_site_connectivity(analysis):
    isc = analysis.get_inter_site_connectivity("bangalore", "singapore")
    assert isc["reachable"] is True
    assert isc["min_latency_ms"] == 55
    assert len(isc["bgp_sessions"]) >= 1


def test_search_devices_by_type(analysis):
    res = analysis.search_devices(device_type="leaf_switch")
    assert res["total"] == 4


def test_search_devices_requires_filter(analysis):
    assert analysis.search_devices()["total"] == 0


def test_unknown_site_raises(analysis):
    with pytest.raises(SiteNotFound):
        analysis.get_site_summary("atlantis")


def test_unknown_device_raises(analysis):
    with pytest.raises(DeviceNotFound):
        analysis.get_device_info("ghost-router")


def test_compare_with_baseline_clean(analysis):
    diff = analysis.compare_with_baseline()
    assert diff["mutations_applied"] == 0
