"""Tests for TwinBuilder, Validator, and TwinManager."""

import copy

import pytest

from graphite.errors import TwinNotInitializedError, ValidationError
from graphite.twin import TwinBuilder, TwinManager
from graphite.twin.validator import Validator


def _node_types(graph):
    from collections import Counter
    return Counter(d.get("node_type") for _, d in graph.nodes(data=True))


def test_builder_loads_complete_graph(baseline_manager):
    g = baseline_manager.baseline
    counts = _node_types(g)
    assert counts["site"] == 4
    assert counts["device"] >= 40
    assert counts["vlan"] >= 10
    assert counts["service"] == 6
    assert counts["user_group"] == 8


def test_every_node_has_node_type(baseline_manager):
    for _, data in baseline_manager.baseline.nodes(data=True):
        assert "node_type" in data


def test_every_edge_relation_matches_key(baseline_manager):
    for _, _, key, data in baseline_manager.baseline.edges(keys=True, data=True):
        assert data.get("relation") == key


def test_physical_links_are_bidirectional(baseline_manager):
    g = baseline_manager.baseline
    for src, dst, key in g.edges(keys=True):
        if key == "physical_link":
            assert g.has_edge(dst, src, key="physical_link")


def test_field_renames_applied(baseline_manager):
    g = baseline_manager.baseline
    dev = g.nodes["blr-core-01"]
    assert dev["device_type"] == "core_switch"
    assert "type" not in dev
    svc = g.nodes["erp-service"]
    assert svc["service_type"] == "web_application"


def test_vlan_status_default_active(baseline_manager):
    assert baseline_manager.baseline.nodes["blr-vlan-420"]["status"] == "active"


def test_bgp_state_merged_onto_device(baseline_manager):
    bgp = baseline_manager.baseline.nodes["blr-edge-01"]["bgp_state"]
    assert bgp["local_as"] == 65001
    assert any(p["peer_device"] == "sg-edge-01" for p in bgp["peers"])


def test_telemetry_merged(baseline_manager):
    assert baseline_manager.baseline.nodes["blr-core-01"]["telemetry"]["cpu_percent"] == 42


def test_manager_clone_is_independent(baseline_manager):
    baseline_manager.clone_working()
    working = baseline_manager.working
    assert working is not baseline_manager.baseline
    working.nodes["blr-core-01"]["status"] = "down"
    assert baseline_manager.baseline.nodes["blr-core-01"]["status"] == "up"


def test_working_before_clone_raises():
    mgr = TwinManager(TwinBuilder.__new__(TwinBuilder))
    with pytest.raises(TwinNotInitializedError):
        _ = mgr.baseline


def test_validator_catches_bad_device():
    errs = Validator.validate_devices([{"id": "x", "type": "nonsense"}])
    assert any("invalid type" in e for e in errs)


def test_validator_detects_duplicate_ids():
    errs = Validator.validate_global_unique_ids(["a", "b"], ["b"])
    assert any("duplicate global ID 'b'" in e for e in errs)


def test_validator_detects_nonreciprocal_bgp():
    entries = [
        {"device": "a", "local_as": 1, "router_id": "1.1.1.1",
         "peers": [{"peer_ip": "2.2.2.2", "peer_device": "b", "peer_as": 2,
                    "state": "established"}]},
        {"device": "b", "local_as": 2, "router_id": "2.2.2.2", "peers": []},
    ]
    errs = Validator.validate_bgp_peers(entries, {"a", "b"})
    assert any("non-reciprocal" in e for e in errs)
