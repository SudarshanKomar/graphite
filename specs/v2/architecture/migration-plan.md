# V1 → V2 Migration Plan

Step-by-step plan for migrating Graphite from custom ToolRegistry to MCP-native architecture.

---

## Migration Principles

1. **One axis at a time**: MCP migration is the single architectural change. No other system redesigns.
2. **Preserve passing tests**: All 94 V1 tests must continue to pass (adapted for MCP where necessary).
3. **Frontend unchanged**: The frontend consumes the same FastAPI endpoints. MCP is backend-internal.
4. **Engines untouched**: `AnalysisEngine`, `SimulationEngine`, `TwinManager`, `GraphWrapper` — zero changes.
5. **Incremental**: Each step is independently testable and committable.

---

## Migration Steps

### Step 1: Add MCP Server (Additive)

**Files created:**
- `graphite/mcp/__init__.py`
- `graphite/mcp/server.py` — `GraphiteMcpServer` class
- `graphite/mcp/tools.py` — tool definitions (ported from `tools/registry.py`)
- `graphite/mcp/resources.py` — resource definitions
- `graphite/mcp/mode.py` — `CapabilityMode` class

**What happens:**
- MCP server is built alongside existing ToolRegistry
- Both systems coexist temporarily
- MCP server wired to same engines as ToolRegistry
- New tests: MCP tool calls return correct results

**Acceptance criteria:**
- [ ] MCP server lists all 36 tools (34 + 2 meta)
- [ ] MCP tool calls produce identical results to ToolRegistry.execute()
- [ ] Mode enforcement works (mutation refused in observe mode)
- [ ] Resources return correct topology/diff data

### Step 2: Agent Migration

**Files modified:**
- `graphite/agent/react_agent.py` — constructor takes `GraphiteMcpServer` instead of `ToolRegistry`
- `graphite/agent/prompts/system_prompt.py` — accepts MCP tool list + mode parameter

**What happens:**
- ReactAgent's `__init__` changes signature
- `_execute_tool` calls MCP server instead of registry
- Query-only whitelist removed (mode enforcement is on MCP server)
- System prompt builder updated for mode awareness

**Acceptance criteria:**
- [ ] Agent completes VLAN-420 scenario via MCP (same result as V1)
- [ ] Agent refuses mutation in observe mode (MCP error, not agent whitelist)
- [ ] Agent can call mutations in operate mode
- [ ] All existing agent tests pass (adapted for MCP)

### Step 3: App Wiring

**Files modified:**
- `graphite/api/app.py` — `build_services` creates MCP server instead of ToolRegistry
- `graphite/api/state.py` — `Services` dataclass updated
- `graphite/api/routes/simulation.py` — simulation endpoints call engines directly (unchanged)
- `graphite/api/routes/agent.py` — mode switching endpoint added

**What happens:**
- FastAPI lifespan wires MCP server
- `Services.registry` replaced with `Services.mcp_server`
- Simulation routes continue calling engines directly (not through MCP)
- New endpoint: `POST /agent/mode` for frontend mode switching (observe/operate)

**Acceptance criteria:**
- [ ] Server starts, health check passes
- [ ] All API tests pass
- [ ] Mode switching via API works
- [ ] Agent endpoint works with MCP backend

### Step 4: Remove ToolRegistry

**Files removed:**
- `graphite/tools/registry.py` (the `build_default_registry` function)
- `graphite/tools/base.py` (`ToolSchema`, `ToolContext`, `ToolRegistry`)
- `graphite/tools/__init__.py`

**Files modified:**
- Any remaining imports of `tools.base` or `tools.registry` removed

**What happens:**
- V1 tool system fully removed
- MCP server is the sole tool interface
- `tests/test_tools.py` rewritten to test MCP tools

**Acceptance criteria:**
- [ ] No imports from `graphite.tools` anywhere in codebase
- [ ] All tests pass
- [ ] Agent works end-to-end

### Step 5: External Agent Support

**Files created:**
- `graphite/mcp/__main__.py` — stdio entry point (`python -m graphite.mcp`)
- Root-level `mcp.json` or documentation for Claude Desktop / IDE config

**What happens:**
- MCP server can run as standalone stdio process
- External agents can connect
- Documentation for IDE integration

**Acceptance criteria:**
- [ ] `python -m graphite.mcp` starts and responds to MCP protocol on stdio
- [ ] Claude Desktop or equivalent can discover and use Graphite tools
- [ ] Tool calls from external agent produce correct results

### Step 6: Frontend Mode Integration (Optional V2)

**Files modified:**
- Frontend: mode selector UI component
- Frontend: mode indicator in header

**What happens:**
- UI shows current mode (Investigation / Simulation)
- User can toggle mode
- Copilot system prompt updates when mode changes

---

## Dependency Changes

### Added
```
mcp >= 1.0
```

### Removed
None (ToolRegistry was not a dependency, it was internal code).

### Unchanged
All existing dependencies (FastAPI, NetworkX, google-generativeai, pydantic-settings, etc.)

---

## Test Migration

| V1 Test File | V2 Change |
|---|---|
| `test_builder.py` | Unchanged |
| `test_graph_wrapper.py` | Unchanged |
| `test_analysis.py` | Unchanged |
| `test_simulation.py` | Unchanged |
| `test_tools.py` | Rewritten → `test_mcp_tools.py` (test MCP tool calls) |
| `test_agent.py` | Adapted (agent constructor change, mock MCP server) |
| `test_api.py` | Adapted (Services uses MCP server) |

**Target**: 94+ tests passing after migration.

---

## Rollback Plan

If MCP migration encounters blocking issues:

1. V1 ToolRegistry code is preserved in git history
2. MCP server and ToolRegistry can coexist (Step 1 state)
3. Agent can be reverted to ToolRegistry in one commit

---

## Timeline Estimate

| Step | Effort | Dependencies |
|---|---|---|
| 1. MCP Server | 2-3 days | None |
| 2. Agent Migration | 1-2 days | Step 1 |
| 3. App Wiring | 1 day | Step 2 |
| 4. Remove ToolRegistry | 0.5 day | Step 3 |
| 5. External Agent | 1-2 days | Step 3 |
| 6. Frontend Mode | 1-2 days | Step 3 |
| **Total** | **~7-11 days** | |
