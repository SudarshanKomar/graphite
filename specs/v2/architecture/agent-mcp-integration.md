# Agent ↔ MCP Integration

How the custom ReAct agent (preserved from V1) becomes an MCP client.

---

## Core Principle

The ReAct loop is unchanged. Only the tool dispatch path changes:

```
V1:  agent._tools.execute(name, params)  →  ToolRegistry  →  engine method
V2:  agent._mcp.call_tool(name, params)  →  MCP Server    →  engine method
```

The agent's thought → action → observation cycle, parse retry logic, corrective feedback, streaming events, and stopping criteria are all preserved exactly as implemented in `react_agent.py`.

---

## Agent Changes (Minimal)

### Before (V1)

```python
class ReactAgent:
    def __init__(self, llm, tool_registry, system_prompt=None, max_iterations=None):
        self._tools = tool_registry
        self._agent_tools = tool_registry.list_agent_tools()
        self._agent_tool_names = {s.name for s in self._agent_tools}
```

### After (V2)

```python
class ReactAgent:
    def __init__(self, llm, mcp_server, system_prompt=None, max_iterations=None):
        self._mcp = mcp_server  # GraphiteMcpServer instance
        self._available_tools = None  # populated lazily from MCP
```

### Tool Discovery

V1 called `registry.list_agent_tools()` at init time.
V2 calls the MCP `tools/list` method, which returns tools filtered by current capability mode:

```python
async def _get_available_tools(self) -> list[Tool]:
    """Get tools from MCP server, respecting current mode."""
    return await self._mcp.list_tools()
```

The system prompt is rebuilt when the mode changes (different tool set → different prompt).

### Tool Execution

V1: `self._tools.execute(tool_name, parameters)` — synchronous, returns dict
V2: `await self._mcp.call_tool(tool_name, parameters)` — async, returns MCP result

```python
async def _execute_tool(self, tool: str, parameters: dict) -> dict:
    """Execute a tool via MCP."""
    try:
        result = await self._mcp.call_tool(tool, parameters)
        # MCP returns list[TextContent]; extract the JSON
        return json.loads(result[0].text)
    except McpError as exc:
        return {"error": exc.code, "message": str(exc)}
```

### Query-Only Enforcement

V1 enforced query-only at the agent level (`_agent_tool_names` whitelist).
V2 enforcement moves to the MCP server (mode-based). The agent no longer needs its own whitelist — the MCP server will refuse mutation calls in observe mode.

However, the system prompt still instructs the agent about its current mode and available tools. This is defense-in-depth: the LLM is told what it can do, AND the server enforces it.

---

## In-Process Transport

The Graphite backend runs the MCP server and the ReAct agent in the same Python process. There is no reason to serialize through stdio or HTTP for internal calls.

### Option A: Direct Method Calls (Recommended for V2)

The agent holds a reference to `GraphiteMcpServer` and calls its handler methods directly:

```python
# In ReactAgent:
tools = await self._mcp.handle_list_tools()
result = await self._mcp.handle_call_tool(name, arguments)
```

This is zero-overhead. No transport, no serialization. The MCP server class is just a Python object.

For external clients (stdio), the same `GraphiteMcpServer` instance is wired to an MCP transport — same handlers, different I/O.

### Option B: InMemoryTransport

The MCP Python SDK may offer an in-memory transport that creates a client/server pair in the same process. This is cleaner from a protocol-purity standpoint but adds unnecessary indirection.

**Decision**: Option A for V2 MVP. The agent calls server methods directly. If MCP SDK standardizes in-process patterns, adopt them.

---

## System Prompt Updates

The system prompt (V1: `build_system_prompt()`) needs these changes:

1. **Tool list**: Generated from MCP `tools/list` response (not `registry.list_agent_tools()`)
2. **Mode awareness**: Prompt includes current mode and its meaning
3. **Meta-tools**: `set_capability_mode` is described (agent can request operate mode when user asks for mutations)
4. **Richer descriptions**: MCP tool descriptions are longer — the prompt formatter should truncate or summarize if token budget is tight

```python
def build_system_prompt(tools: list[Tool], mode: str, max_iterations: int) -> str:
    mode_guidance = {
        "observe": "You are in OBSERVE mode. Use read-only query tools to inspect topology, analyze impact, and investigate issues. You cannot modify topology state.",
        "operate": "You are in OPERATE mode. You have full topology control. You can inspect, mutate (break/fix/simulate), and verify. Use mutation tools for faults, remediation, or what-if analysis as the user requests."
    }
    # ... render tools + mode guidance + output contract
```

---

## Event Streaming (Unchanged)

Agent events (`ThoughtEvent`, `ToolCallEvent`, `ToolResultEvent`, `FinalAnswerEvent`, `ErrorEvent`) are unchanged. The SSE streaming from `POST /agent/query` works exactly as before. The frontend needs no changes for the MCP migration.

---

## Sequence Diagram — Observe Mode

```
User → FastAPI → ReactAgent.run("WiFi users can't connect")
    Agent → MCP Server: list_tools()
    Agent ← MCP Server: [21 query + 2 meta + 13 mutation (annotated as requires operate)]
    Agent → LLM: system_prompt + user_query
    Agent ← LLM: {thought, action: {tool: "get_site_summary", params: {site: "bangalore"}}}
    Agent → MCP Server: call_tool("get_site_summary", {site: "bangalore"})
    MCP Server → AnalysisEngine: get_site_summary("bangalore")
    MCP Server ← AnalysisEngine: {site, health: "degraded", ...}
    Agent ← MCP Server: TextContent(json)
    Agent → SSE: ThoughtEvent, ToolCallEvent, ToolResultEvent
    ... (loop continues) ...
    Agent → SSE: FinalAnswerEvent
```

---

## Migration Path for ReactAgent

| Component | V1 | V2 | Change Size |
|---|---|---|---|
| Constructor | `tool_registry: ToolRegistry` | `mcp_server: GraphiteMcpServer` | Small (type change) |
| Tool discovery | `registry.list_agent_tools()` | `mcp.handle_list_tools()` | Small |
| Tool execution | `registry.execute(name, params)` | `mcp.handle_call_tool(name, args)` | Small (+ async + JSON parse) |
| Query enforcement | Agent-side whitelist | MCP server-side mode check (observe/operate) | Removed from agent |
| System prompt | `build_system_prompt(tools, max_iter)` | `build_system_prompt(tools, mode, max_iter)` | +mode param |
| Streaming events | Unchanged | Unchanged | None |
| Parse/retry logic | Unchanged | Unchanged | None |
| Stopping criteria | Unchanged | Unchanged | None |

**Total agent code change**: ~30 lines modified out of ~184.
