# ADR-003: Agent Framework Selection

**Status**: Accepted  
**Date**: 2025-06-22  
**Deciders**: Architecture Lead  

---

## Context

Graphite needs an AI agent capable of:
- Investigating network issues by calling tools
- Reasoning about topology, failures, and dependencies
- Explaining root causes in natural language
- Suggesting remediation actions

The agent must be custom-built (no LangChain/LangGraph). We need to select an orchestration pattern.

## Decision

Use a **ReAct (Reasoning + Acting) agent** with structured tool dispatch.

### Why ReAct

1. **Simplicity**: Single thought → action → observation loop. No planner/executor split, no multi-agent coordination.
2. **Transparency**: Every reasoning step is visible. The trace IS the demo value — showing the agent's investigative process.
3. **Proven pattern**: Well-understood, works reliably with modern LLMs for tool-use tasks.
4. **Sufficient for scope**: All 3 MVP demo scenarios are single-investigator workflows. No need for parallel agents or hierarchical planning.

### Agent Loop

```
while not done and iterations < MAX_ITERATIONS:
    1. Send conversation history + system prompt to LLM
    2. LLM returns structured response:
       - thought: string (reasoning about what to do next)
       - action: {tool_name, parameters} | {final_answer: string}
    3. If action is final_answer → return result, exit loop
    4. Execute tool, get observation (tool result)
    5. Append thought + action + observation to conversation history
    6. iterations += 1
```

### Structured Output Format

LLM responses are structured JSON, not free-form text:

```json
{
    "thought": "The user reports WiFi issues in Bangalore. I should check VLAN 420 status first.",
    "action": {
        "tool": "get_vlan_info",
        "parameters": {
            "vlan_id": 420,
            "site": "bangalore"
        }
    }
}
```

Final answer format:

```json
{
    "thought": "I've identified the root cause and can now provide a complete analysis.",
    "action": {
        "tool": "final_answer",
        "parameters": {
            "summary": "VLAN 420 has been removed from the Bangalore campus...",
            "root_cause": "VLAN 420 (Corp WiFi) was removed from core switches...",
            "affected_components": {
                "devices": ["blr-access-01", "blr-access-02", "..."],
                "services": ["auth-service (degraded)", "erp-service (degraded)"],
                "users": {"count": 5000, "groups": ["corp-wifi-users"]}
            },
            "severity": "critical",
            "confidence": 0.95,
            "remediation": [
                "Restore VLAN 420 on blr-core-01 and blr-core-02",
                "Verify trunk ports on distribution switches",
                "Confirm WiFi AP SSID mapping to VLAN 420"
            ]
        }
    }
}
```

### System Prompt Design

The system prompt contains:
1. **Role**: Network operations copilot
2. **Available tools**: Name, description, parameters, return type for each tool
3. **Instructions**: How to reason, when to use which tools, output format
4. **Constraints**: Use tools for facts (never guess network state), always verify before concluding

### Stopping Criteria

The agent stops when:
- It calls `final_answer` (normal termination)
- Iteration count reaches `MAX_ITERATIONS` (default: 15) — returns partial analysis with disclaimer
- LLM returns malformed output after 3 retries — returns error

### Memory / Context

For MVP, **conversation history IS the memory**. No external memory store.

Each conversation is stateless across sessions. Within a session:
- Tool results accumulate in the conversation history
- The LLM sees all prior thoughts, actions, and observations
- This provides sufficient context for 5-15 step investigations

### Error Handling

- Tool execution errors (invalid device_id, etc.) are returned as observations with error messages
- Agent is expected to adapt (try different tool, ask for clarification)
- LLM parse errors trigger retry with error feedback (up to 3 retries)

### LLM Provider

Abstract behind a simple interface:

```python
class LLMProvider(Protocol):
    async def complete(self, messages: list[Message], tools: list[ToolSchema]) -> AgentResponse: ...
```

Support Gemini and mock providers as backends. Configure via environment variable. Default: Gemini 2.5 Flash.

Use the LLM's native tool-calling / function-calling API where available, with a fallback to JSON-in-text parsing.

## Consequences

**Positive:**
- Simple to implement (~200 lines for core loop)
- Easy to debug (linear trace)
- Demo-friendly (show each reasoning step)
- No framework dependencies

**Negative:**
- Sequential tool calls only (no parallel investigation)
- No hierarchical task decomposition
- May struggle with very complex multi-hop reasoning (mitigated by good tool design)

**Acceptable for MVP:**
The demo scenarios require 5-15 tool calls each. ReAct handles this comfortably. If future scenarios require parallel investigation or multi-agent coordination, this can be extended.

## Alternatives Considered

### 1. Planner-Executor
LLM generates a plan, executor runs it. Rejected: adds complexity, plans often need revision mid-execution anyway (ReAct handles this naturally by re-reasoning each step).

### 2. Multi-Agent (Router + Specialists)
Topology agent, BGP agent, service agent, etc. Rejected: coordination overhead, prompt engineering for routing, all specialists need the same graph access anyway. Single agent with good tools is simpler and sufficient.

### 3. LangChain/LangGraph
Pre-built frameworks. Rejected per project requirements (custom implementation). Also adds heavy dependencies and abstraction layers that obscure what's happening.

## Implementation Notes

- Core agent in `graphite/agent/react_agent.py`
- Tool registry in `graphite/tools/registry.py`
- LLM providers in `graphite/agent/llm/`
- System prompt template in `graphite/agent/prompts/`
- Agent returns streaming events for frontend: `thought`, `tool_call`, `tool_result`, `final_answer`
- FastAPI endpoint streams these events via Server-Sent Events (SSE)
