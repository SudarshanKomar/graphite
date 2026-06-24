"""Tests for the FastAPI layer using Starlette's TestClient."""

import json

import pytest
from fastapi.testclient import TestClient

from graphite.agent.llm import MockProvider
from graphite.api import create_app
from graphite.config import Settings


def _settings():
    # Deterministic: no real key, data dir resolves to backend/network_state.
    return Settings(gemini_api_key="")


def _client(llm_provider=None):
    app = create_app(settings=_settings(), llm_provider=llm_provider)
    return TestClient(app)


def _tool_call(tool, **params):
    return json.dumps({"thought": "checking", "action": {"tool": tool, "parameters": params}})


def _final(**kw):
    payload = {"summary": "VLAN 420 removal disconnects 5000 users", "root_cause": "rc",
               "severity": "critical", "confidence": 0.9, "remediation": ["restore vlan"],
               "affected_components": {"users": {"count": 5000}}}
    payload.update(kw)
    return json.dumps({"thought": "done", "action": {"tool": "final_answer", "parameters": payload}})


@pytest.fixture
def client():
    return _client()


# --- Health / root ---------------------------------------------------------
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["sites"] == 4
    assert body["devices"] >= 40
    assert body["llm_configured"] is False


def test_root(client):
    assert client.get("/").json()["name"] == "graphite"


# --- Topology --------------------------------------------------------------
def test_list_sites(client):
    body = client.get("/topology/sites").json()
    assert body["total"] == 4
    blr = next(s for s in body["sites"] if s["site"] == "bangalore")
    assert blr["health"] == "healthy"


def test_site_topology(client):
    body = client.get("/topology/sites/singapore").json()
    ids = {d["id"] for d in body["devices"]}
    assert "sg-leaf-03" in ids


def test_site_not_found_returns_404(client):
    r = client.get("/topology/sites/atlantis")
    assert r.status_code == 404
    assert r.json()["error"] == "SiteNotFound"


def test_device_info(client):
    body = client.get("/topology/devices/blr-core-01").json()
    assert body["device_type"] == "core_switch"


def test_search_devices(client):
    body = client.get("/topology/search", params={"device_type": "leaf_switch"}).json()
    assert body["total"] == 4


# --- Analysis --------------------------------------------------------------
def test_blast_radius_endpoint(client):
    body = client.get("/analysis/blast-radius/blr-vlan-420").json()
    assert body["severity"] == "critical"
    assert body["total_users_affected"] == 5000


def test_trace_endpoint(client):
    body = client.get("/analysis/trace",
                      params={"source": "blr-corp-wifi-users", "destination": "erp-service"}).json()
    assert body["reachable"] is True


def test_spof_endpoint(client):
    body = client.get("/analysis/spof/singapore").json()
    ids = {s["component_id"] for s in body["single_points_of_failure"]}
    assert "sg-leaf-03" in ids


# --- Simulation ------------------------------------------------------------
def test_mutate_remove_vlan_and_diff_and_reset(client):
    r = client.post("/simulation/mutate", json={
        "mutation_type": "remove_vlan",
        "parameters": {"vlan_id": 420, "site": "bangalore"},
    })
    assert r.status_code == 200
    assert r.json()["result"]["cascading_effects"]["total_users_affected"] == 5000

    diff = client.get("/simulation/diff").json()
    assert diff["mutations_applied"] >= 1
    assert any(c["change_type"] == "vlan_removed" for c in diff["changes"])

    assert client.post("/simulation/reset").json()["status"] == "reset"
    assert client.get("/simulation/diff").json()["mutations_applied"] == 0


def test_mutate_unknown_type_returns_400(client):
    r = client.post("/simulation/mutate", json={"mutation_type": "explode", "parameters": {}})
    assert r.status_code == 400


def test_mutate_domain_error_returns_404(client):
    r = client.post("/simulation/mutate", json={
        "mutation_type": "disable_device", "parameters": {"device_id": "ghost"},
    })
    assert r.status_code == 404
    assert r.json()["error"] == "DeviceNotFound"


def test_mutate_invalid_state_returns_409(client):
    client.post("/simulation/mutate", json={
        "mutation_type": "remove_vlan", "parameters": {"vlan_id": 420, "site": "bangalore"}})
    r = client.post("/simulation/mutate", json={
        "mutation_type": "remove_vlan", "parameters": {"vlan_id": 420, "site": "bangalore"}})
    assert r.status_code == 409


# --- Agent -----------------------------------------------------------------
def test_agent_query_non_streaming():
    provider = MockProvider(responses=[
        _tool_call("get_blast_radius", component_id="blr-vlan-420"),
        _final(),
    ])
    client = _client(llm_provider=provider)
    r = client.post("/agent/query", json={"query": "What if VLAN 420 is removed?", "stream": False})
    assert r.status_code == 200
    body = r.json()
    assert body["final"]["severity"] == "critical"
    tool_results = [e for e in body["events"] if e["type"] == "tool_result"]
    assert tool_results[0]["result"]["total_users_affected"] == 5000


def test_agent_query_streaming_sse():
    provider = MockProvider(responses=[
        _tool_call("get_blast_radius", component_id="blr-vlan-420"),
        _final(),
    ])
    client = _client(llm_provider=provider)
    r = client.post("/agent/query", json={"query": "What if VLAN 420 is removed?", "stream": True})
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    text = r.text
    assert "tool_call" in text
    assert "final_answer" in text
    assert '"type": "done"' in text


def test_agent_query_without_llm_returns_503(client):
    r = client.post("/agent/query", json={"query": "hi", "stream": False})
    assert r.status_code == 503
