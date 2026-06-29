"""Tests for the ReAct agent loop using a deterministic mock LLM."""

import json

import pytest

from graphite.agent import ReactAgent, parse_agent_response
from graphite.agent.parser import AgentParseError
from graphite.agent.llm import MockProvider


def _tool_call(thought, tool, **params):
    return json.dumps({"thought": thought, "action": {"tool": tool, "parameters": params}})


def _final(summary="done", **kw):
    payload = {"summary": summary, "root_cause": "rc", "severity": "critical",
               "confidence": 0.9, "remediation": ["step"], "affected_components": {}}
    payload.update(kw)
    return json.dumps({"thought": "concluding", "action": {"tool": "final_answer",
                                                           "parameters": payload}})


# --- Parser ----------------------------------------------------------------
def test_parser_plain_json():
    resp = parse_agent_response('{"thought":"t","action":{"tool":"x","parameters":{"a":1}}}')
    assert resp.action.tool == "x"
    assert resp.action.parameters == {"a": 1}


def test_parser_strips_code_fences():
    raw = "```json\n{\"thought\":\"t\",\"action\":{\"tool\":\"x\",\"parameters\":{}}}\n```"
    resp = parse_agent_response(raw)
    assert resp.action.tool == "x"


def test_parser_extracts_embedded_object():
    raw = "Here you go:\n{\"thought\":\"t\",\"action\":{\"tool\":\"x\",\"parameters\":{}}} thanks"
    resp = parse_agent_response(raw)
    assert resp.action.tool == "x"


def test_parser_rejects_garbage():
    with pytest.raises(AgentParseError):
        parse_agent_response("not json at all")


# --- Full investigation flow (VLAN 420) ------------------------------------
async def test_agent_investigates_vlan_removal(mcp_server):
    provider = MockProvider(responses=[
        _tool_call("Check blast radius of VLAN 420", "get_blast_radius",
                   component_id="blr-vlan-420"),
        _final(summary="VLAN 420 removal disconnects 5000 users"),
    ])
    agent = ReactAgent(provider, mcp_server)
    result = await agent.investigate("What happens if VLAN 420 is removed?")

    types = [e["type"] for e in result["events"]]
    assert types == ["thought", "tool_call", "tool_result", "thought", "final_answer"]

    tool_result = next(e for e in result["events"] if e["type"] == "tool_result")
    assert tool_result["result"]["severity"] == "critical"
    assert tool_result["result"]["total_users_affected"] == 5000

    assert result["final"]["severity"] == "critical"
    assert result["final"]["confidence"] == 0.9


# --- Malformed output recovery ---------------------------------------------
async def test_agent_recovers_from_malformed_output(mcp_server):
    provider = MockProvider(responses=[
        "I think the answer is... (no JSON here)",   # unparseable
        _final(summary="recovered"),                  # valid on retry
    ])
    agent = ReactAgent(provider, mcp_server)
    result = await agent.investigate("Why is the network slow?")
    assert result["final"] is not None
    assert result["final"]["summary"] == "recovered"


async def test_agent_errors_after_max_parse_retries(mcp_server):
    provider = MockProvider(responses=["bad", "still bad", "nope"])
    agent = ReactAgent(provider, mcp_server)
    events = [e async for e in agent.run("q")]
    assert events[-1].type == "error"


# --- Mode enforcement (V2: MCP server enforces, not the agent) -------------
async def test_agent_refuses_mutation_in_observe_mode(mcp_server):
    """In observe mode, mutation tools return a ModeViolation observation."""
    provider = MockProvider(responses=[
        _tool_call("Try to disable a device", "disable_device", device_id="blr-core-01"),
        _final(summary="not allowed"),
    ])
    agent = ReactAgent(provider, mcp_server)
    result = await agent.investigate("Disable blr-core-01")
    tool_result = next(e for e in result["events"] if e["type"] == "tool_result")
    assert tool_result["result"]["error"] == "ModeViolation"


async def test_agent_handles_unknown_tool(mcp_server):
    provider = MockProvider(responses=[
        _tool_call("Call a made-up tool", "teleport", target="moon"),
        _final(summary="adapted"),
    ])
    agent = ReactAgent(provider, mcp_server)
    result = await agent.investigate("q")
    tr = next(e for e in result["events"] if e["type"] == "tool_result")
    assert tr["result"]["error"] == "ToolNotAvailable"


# --- Domain error surfaced as observation ----------------------------------
async def test_agent_surfaces_domain_error(mcp_server):
    provider = MockProvider(responses=[
        _tool_call("Look up a missing device", "get_device_info", device_id="ghost"),
        _final(summary="device not found"),
    ])
    agent = ReactAgent(provider, mcp_server)
    result = await agent.investigate("q")
    tr = next(e for e in result["events"] if e["type"] == "tool_result")
    assert tr["result"]["error"] == "DeviceNotFound"


# --- Max iterations stop ---------------------------------------------------
async def test_agent_stops_at_max_iterations(mcp_server):
    def handler(messages, tools):
        return _tool_call("keep going", "get_site_summary", site="bangalore")

    provider = MockProvider(handler=handler)
    agent = ReactAgent(provider, mcp_server, max_iterations=2)
    events = [e async for e in agent.run("q")]
    final = events[-1]
    assert final.type == "final_answer"
    assert final.severity == "unknown"  # truncated fallback
