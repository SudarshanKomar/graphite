# MCP Server Design

Detailed design for the Graphite MCP Server — the canonical interface to all digital twin capabilities.

---

## Server Identity

```python
server = Server("graphite-network-copilot")
```

The server name is used by MCP clients for discovery and configuration.

---

## Module Location

```
backend/graphite/mcp/
├── __init__.py
├── server.py          # Server definition, tool/resource registration
├── tools.py           # Tool handler implementations
├── resources.py       # Resource handler implementations
└── mode.py            # Capability mode state management
```

The MCP server is a peer to the existing `api/`, `agent/`, `tools/` packages. It imports from `analysis/` and `simulation/` — the same engines the V1 ToolRegistry used.

---

## Dependency on MCP SDK

```
mcp >= 1.0
```

Use the official `mcp` Python package which provides `Server`, `Tool`, `Resource`, and transport helpers. The package is maintained by Anthropic and is the reference implementation.

---

## Tool Registration

All 34 V1 tools map to MCP tools with enhanced metadata. The MCP SDK uses decorators or explicit registration.

### Example Tool Registration

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("graphite-network-copilot")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return all tools. Mutation tools are always listed for discoverability
    but annotated with mode requirements. Enforcement is in call_tool()."""
    return ALL_TOOLS  # 36 tools always visible; mode enforcement at call time

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch a tool call to the appropriate engine."""
    tool_def = TOOL_MAP.get(name)
    if not tool_def:
        raise McpError(INVALID_PARAMS, f"Unknown tool: {name}")
    
    # Mode enforcement (ADR-007)
    if tool_def.category == "mutation" and mode.current == "observe":
        raise McpError(
            INVALID_REQUEST,
            f"Tool '{name}' modifies topology state. Current mode: observe. "
            "Switch to operate mode: set_capability_mode(mode='operate')"
        )
    
    result = tool_def.handler(arguments)
    return [TextContent(type="text", text=json.dumps(result))]
```

### Tool Metadata Enrichment

V1 tool descriptions were minimal one-liners because the system prompt carried semantics. In MCP, the tool description IS the primary documentation for external agents that have no Graphite system prompt.

Each V1 tool gets an enriched description for MCP:

| V1 Description | V2 MCP Description |
|---|---|
| `"Device metadata and status."` | `"Returns metadata and current status for a network device including type, vendor, OS, site, management IP, and operational status (up/down). Use this to inspect a specific device by its ID (e.g. 'blr-core-01')."` |
| `"Full impact of a failed component."` | `"Computes the blast radius of a failed or degraded network component. Accepts a device ID, VLAN node ID (e.g. 'blr-vlan-420'), service ID, or link ID. Returns affected devices, services, user groups, total impacted users, severity (critical/high/medium/low), and severity factors."` |

### Input Schema Enhancement

V1 used minimal JSON Schema (`{"type": "string"}`). V2 MCP tool schemas include:
- `description` on each parameter
- `enum` constraints where applicable (e.g., scope: site|wan|all)
- Example values in descriptions

```python
Tool(
    name="get_links",
    description="List network links filtered by scope. "
                "'site' returns intra-site links (requires 'site' param), "
                "'wan' returns inter-site WAN/MPLS/VPN links, "
                "'all' returns every link.",
    inputSchema={
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["site", "wan", "all"],
                "description": "Filter scope for link listing"
            },
            "site": {
                "type": "string",
                "description": "Site short name (required when scope='site'). "
                               "Values: bangalore, london, newyork, singapore"
            }
        },
        "required": ["scope"]
    }
)
```

---

## Resource Registration

Three curated MCP resources provide browsable read-only state for external agents.

### `graphite://topology/overview`

Returns a high-level network overview: all sites with health, device counts, and WAN link status. Equivalent to the data behind the global topology view.

### `graphite://topology/sites/{site}`

Returns full topology of a specific site: devices, links, VLANs, services, user groups. Parameterized by site short name.

### `graphite://state/diff`

Returns the current working-twin-vs-baseline diff. Empty when no mutations are active.

### Resource Implementation

```python
@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(uri="graphite://topology/overview", name="Network Overview",
                 description="Global topology: sites, health, WAN links"),
        Resource(uri="graphite://state/diff", name="Current Mutations",
                 description="Changes applied to working twin vs baseline"),
        # Plus per-site resources generated dynamically
    ]

@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "graphite://topology/overview":
        return json.dumps(analysis_engine.get_global_overview())
    if uri == "graphite://state/diff":
        return json.dumps(analysis_engine.compare_with_baseline())
    if uri.startswith("graphite://topology/sites/"):
        site = uri.split("/")[-1]
        return json.dumps(analysis_engine.get_site_topology(site))
    raise McpError(RESOURCE_NOT_FOUND, f"Unknown resource: {uri}")
```

---

## Server Lifecycle

### Startup

The MCP server needs references to the analysis and simulation engines. These are injected at construction time — same wiring pattern as V1's `ToolContext`.

```python
class GraphiteMcpServer:
    def __init__(self, analysis_engine, simulation_engine, twin_manager):
        self._analysis = analysis_engine
        self._simulation = simulation_engine
        self._twin = twin_manager
        self._mode = CapabilityMode()  # default: observe
        self._server = Server("graphite-network-copilot")
        self._register_tools()
        self._register_resources()
```

### Internal (In-Process) Usage

The Graphite ReAct agent uses the MCP server in-process. No network transport. The agent calls server methods directly or via `InMemoryTransport`:

```python
# In app.py lifespan:
mcp_server = GraphiteMcpServer(analysis_engine, simulation_engine, twin_manager)
agent = ReactAgent(llm_provider, mcp_server)
```

### External (stdio) Usage

For IDE integration, the MCP server runs as a standalone stdio process:

```bash
python -m graphite.mcp
```

This boots the twin, engines, and MCP server on stdio transport. Configuration via `mcp.json` or Claude Desktop config:

```json
{
    "mcpServers": {
        "graphite": {
            "command": "python",
            "args": ["-m", "graphite.mcp"],
            "cwd": "/path/to/backend"
        }
    }
}
```

---

## What Graphite Does NOT Expose via MCP

| Concern | MCP | Why Not |
|---|---|---|
| FastAPI REST endpoints | No | REST is for the frontend/operator. MCP is for agents. |
| Agent SSE streaming | No | The agent loop is a consumer of MCP, not an MCP feature. |
| MCP Prompts | No (V2) | External agents compose their own prompts. Internal agent has its system prompt. |
| Working twin reset | Via tool | `reset_simulation` — meta-tool, available in all modes. |
| Mode switching | Via tool | `set_capability_mode` — meta-tool (observe / operate). |
