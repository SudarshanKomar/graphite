# V2 Implementation Roadmap

Phased plan for migrating Graphite from V1 ToolRegistry to V2 MCP-native architecture. Each phase is independently testable and committable.

---

## Guiding Principles

1. **Engines unchanged**: `AnalysisEngine`, `SimulationEngine`, `TwinManager`, `GraphWrapper` — zero modifications.
2. **Frontend unchanged in MCP phases**: The frontend consumes FastAPI REST. MCP is backend-internal. Frontend mode UI is a separate phase.
3. **Tests never break**: Each phase ends with all tests passing (new + adapted).
4. **Additive first, remove later**: MCP server is built alongside ToolRegistry before the registry is removed.
5. **One deployable per phase**: Each phase produces a working server.

---

## Phase 1 — MCP Server Foundation

**Goal**: Build the Graphite MCP Server alongside the existing ToolRegistry. Both coexist. No agent or API changes.

### Modules Created

| File | Purpose |
|---|---|
| `graphite/mcp/__init__.py` | Package init |
| `graphite/mcp/server.py` | `GraphiteMcpServer` class — tool/resource registration, mode enforcement, dispatch |
| `graphite/mcp/tools.py` | 34 tool definitions ported from `tools/registry.py` + 2 meta-tools (`set_capability_mode`, `reset_simulation`) |
| `graphite/mcp/resources.py` | 3 MCP resources (topology overview, site topology, state diff) |
| `graphite/mcp/mode.py` | `CapabilityMode` enum + state holder (observe / operate) |

### What Happens
- MCP server is instantiated with same engine references as ToolRegistry
- All 36 tools registered with enriched MCP descriptions (multi-sentence, examples, enum constraints)
- Mode enforcement: mutation tools refused in observe mode
- Resources read from AnalysisEngine queries

### Dependencies
- Add `mcp >= 1.0` to `requirements.txt` / `pyproject.toml`
- No other dependency changes

### Risks
- MCP SDK API surface may differ from spec examples (mitigate: read SDK docs first, build one tool end-to-end before porting all 34)
- Corporate proxy may block pip install of `mcp` package (mitigate: `--trusted-host` flags as in V1)

### Validation
- [ ] `GraphiteMcpServer` instantiates without error
- [ ] `handle_list_tools()` returns 36 tools with correct schemas
- [ ] `handle_call_tool("get_device_info", {"device_id": "blr-core-01"})` returns same result as `registry.execute("get_device_info", {"device_id": "blr-core-01"})`
- [ ] Parity test: every tool call through MCP matches ToolRegistry output
- [ ] Mode enforcement: mutation in observe mode → `McpError`
- [ ] Mode enforcement: mutation in operate mode → success
- [ ] `set_capability_mode` toggles between observe/operate
- [ ] `reset_simulation` clears working twin
- [ ] Resources return valid JSON for overview, per-site, diff
- [ ] All 94 existing V1 tests still pass (MCP is additive, no V1 code touched)

**Estimated effort**: 2–3 days

---

## Phase 2 — Agent Migration

**Goal**: Switch the ReAct agent from ToolRegistry to MCP server. Remove agent-side query-only whitelist.

### Modules Modified

| File | Change |
|---|---|
| `graphite/agent/react_agent.py` | Constructor: `tool_registry: ToolRegistry` → `mcp_server: GraphiteMcpServer`. `_execute_tool` calls MCP. Remove `_agent_tool_names` whitelist. |
| `graphite/agent/prompts/system_prompt.py` | Accept MCP tool list + mode parameter. Mode-aware guidance text. |

### What Happens
- Agent discovers tools via `mcp_server.handle_list_tools()`
- Agent calls tools via `mcp_server.handle_call_tool(name, args)`
- Query-only enforcement removed from agent (MCP server handles it via mode)
- System prompt rebuilt to include mode guidance (observe/operate)
- Tool descriptions now come from enriched MCP metadata

### Risks
- System prompt token budget: enriched descriptions are longer. Mitigate: truncate or summarize in prompt builder if needed.
- Agent parse/retry logic unchanged, but tool result format changes slightly (JSON wrapped in MCP TextContent). Mitigate: `_execute_tool` extracts JSON from TextContent.

### Validation
- [ ] Agent completes VLAN-420 investigation via MCP (observe mode) — same quality as V1
- [ ] Agent in observe mode: attempt to call `disable_device` → receives error observation, adapts
- [ ] Agent in operate mode: can call `disable_device` → receives result
- [ ] System prompt includes mode guidance text
- [ ] All agent tests pass (adapted for MCP constructor)

**Estimated effort**: 1–2 days

---

## Phase 3 — App Wiring + Mode API

**Goal**: Wire MCP server into FastAPI `Services`. Add REST mode-switching endpoint. ToolRegistry still present but unused by agent.

### Modules Modified

| File | Change |
|---|---|
| `graphite/api/state.py` | `Services` dataclass: `registry` field → `mcp_server` field |
| `graphite/api/app.py` | `build_services` creates `GraphiteMcpServer` instead of (or alongside) ToolRegistry |
| `graphite/api/routes/agent.py` | `POST /agent/mode` — switch observe/operate. `POST /agent/query` — passes mode-aware MCP server to agent. |
| `graphite/api/routes/simulation.py` | Simulation endpoints call engines directly (unchanged). No MCP routing. |

### What Happens
- `Services.mcp_server` replaces `Services.registry` for agent usage
- Simulation REST endpoints (mutate/reset/diff) continue calling engines directly (they are operator-facing REST, not agent-facing MCP)
- New endpoint: `POST /agent/mode` accepts `{"mode": "observe" | "operate"}`
- Agent endpoint checks current mode and passes to agent's system prompt builder

### Risks
- `build_services` wiring change must be careful to preserve simulation endpoint behavior
- API test fixtures need `mcp_server` instead of `registry`

### Validation
- [ ] `GET /health` returns 200
- [ ] `POST /agent/mode` switches mode, returns current mode
- [ ] Agent query in observe mode works correctly
- [ ] Agent query in operate mode works correctly
- [ ] All simulation endpoints (mutate/reset/diff) work unchanged
- [ ] All API tests pass (adapted)

**Estimated effort**: 1 day

---

## Phase 4 — Remove ToolRegistry

**Goal**: Delete V1 tool system. MCP server is sole tool interface.

### Modules Removed

| File | Reason |
|---|---|
| `graphite/tools/registry.py` | Replaced by `graphite/mcp/tools.py` |
| `graphite/tools/base.py` | `ToolSchema`, `ToolContext`, `ToolRegistry` replaced by MCP equivalents |
| `graphite/tools/__init__.py` | Package no longer needed |

### Modules Modified
- Any remaining imports of `graphite.tools` — removed
- `tests/test_tools.py` → rewritten as `tests/test_mcp_tools.py`

### Validation
- [ ] `grep -r "graphite.tools" backend/` returns zero hits (excluding test history)
- [ ] All tests pass
- [ ] Agent works end-to-end
- [ ] Server starts cleanly

**Estimated effort**: 0.5 day

---

## Phase 5 — External Agent Support (stdio)

**Goal**: Graphite MCP server runs as standalone stdio process for IDE integration.

### Modules Created

| File | Purpose |
|---|---|
| `graphite/mcp/__main__.py` | Entry point: boots twin, engines, MCP server on stdio transport |
| `mcp.json` (repo root) | MCP server configuration for Claude Desktop / IDE discovery |

### What Happens
- `python -m graphite.mcp` starts the MCP server on stdio
- Boots `TwinBuilder` → `TwinManager` → engines → `GraphiteMcpServer` → stdio transport
- External agents can connect and call tools
- Same mode enforcement, same tool surface, same engine behavior

### Risks
- MCP SDK stdio transport API may require specific initialization patterns
- Twin initialization time (~1s) acceptable for stdio startup

### Validation
- [ ] `python -m graphite.mcp` starts without error, responds to MCP `initialize` handshake
- [ ] External client can `tools/list` and receives 36 tools
- [ ] External client can call `get_site_summary(site="bangalore")` and get valid response
- [ ] Mode enforcement works over stdio (mutation refused in observe, allowed in operate)
- [ ] `mcp.json` allows Claude Desktop / Windsurf configuration

**Estimated effort**: 1–2 days

---

## Phase 6 — Frontend Mode Integration

**Goal**: Graphite UI shows current capability mode and allows toggling.

### Modules Modified

| File | Change |
|---|---|
| `frontend/src/lib/store.ts` | Add `capabilityMode: "observe" | "operate"` to store |
| `frontend/src/lib/api.ts` | Add `setMode(mode)` and `getMode()` API calls |
| `frontend/src/components/console/Header.tsx` | Mode badge (green=observe, amber=operate) + toggle button |
| `frontend/src/components/copilot/Copilot.tsx` | Show current mode in copilot header area |

### What Happens
- Header shows current mode with colored badge
- User can toggle Observe ↔ Operate
- Toggle calls `POST /agent/mode`
- When agent performs mutation in operate mode, topology auto-refreshes to show state change

### Validation
- [ ] Mode badge renders correctly (green/amber)
- [ ] Toggle calls API and updates store
- [ ] Agent query in operate mode → mutation → topology refresh shows updated state
- [ ] `next build` compiles cleanly

**Estimated effort**: 1–2 days

---

## Phase Summary

| Phase | Goal | Effort | Cumulative |
|---|---|---|---|
| 1 | MCP server (additive) | 2–3d | 2–3d |
| 2 | Agent migration | 1–2d | 3–5d |
| 3 | App wiring + mode API | 1d | 4–6d |
| 4 | Remove ToolRegistry | 0.5d | 4.5–6.5d |
| 5 | External agent (stdio) | 1–2d | 5.5–8.5d |
| 6 | Frontend mode UI | 1–2d | 6.5–10.5d |
| **Total** | | | **~7–11 days** |

---

## Rollback Strategy

- **Phase 1**: Purely additive. Revert = delete `graphite/mcp/`. Zero risk.
- **Phase 2–3**: ToolRegistry still exists. Agent can be reverted to ToolRegistry in one commit.
- **Phase 4**: After ToolRegistry removal, rollback requires restoring from git history. Do not start Phase 4 until Phase 2–3 are validated end-to-end.
- **Phase 5–6**: Independent features. Can be deferred without affecting core functionality.

---

## Test Plan

| V1 Test File | V2 Disposition |
|---|---|
| `test_builder.py` | Unchanged |
| `test_graph_wrapper.py` | Unchanged |
| `test_analysis.py` | Unchanged |
| `test_simulation.py` | Unchanged |
| `test_tools.py` | Phase 4: rewritten → `test_mcp_tools.py` |
| `test_agent.py` | Phase 2: adapted (MCP constructor, mock MCP server) |
| `test_api.py` | Phase 3: adapted (Services uses MCP server) |
| **New: `test_mcp_server.py`** | Phase 1: MCP server unit tests (tool parity, mode enforcement, resources) |

**Target**: 94+ tests after each phase.
