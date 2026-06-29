# MVP Roadmap

Phased implementation plan with dependencies, acceptance criteria, and estimated effort.

---

## Phase Overview

| Phase | Name | Depends On | Est. Effort |
|---|---|---|---|
| 1 | JSON Data + Twin Builder | — | 2-3 days |
| 2 | Graph Wrapper + Analysis Engine (Core) | Phase 1 | 3-4 days |
| 3 | Simulation Engine + Tools | Phase 2 | 3-4 days |
| 4 | Agent Implementation | Phase 3 | 2-3 days |
| 5 | API Layer | Phase 4 | 1-2 days |
| 6 | Frontend | Phase 5 | 4-5 days |
| 7 | Demo Scenario Integration & Polish | Phase 6 | 2-3 days |
| **Total** | | | **~18-24 days** |

---

## Phase 1: JSON Data + Twin Builder

**Goal**: Create realistic JSON network data and build the graph from it.

### Tasks

1. **Create site JSON files** (`sites/bangalore.json`, `london.json`, `newyork.json`, `singapore.json`)
   - All fields per schema spec

2. **Create devices.json**
   - Bangalore: 2 edge routers, 2 firewalls, 2 core switches, 4 distribution switches, ~10 aggregated access switches, ~5 aggregated AP groups
   - London: 2 edge routers, 2 core switches, ~5 aggregated access switches
   - New York: 2 edge routers, 2 core switches, ~4 aggregated access switches
   - Singapore DC: 2 spine switches, 4 leaf switches, 4 server nodes
   - Total: ~50-60 devices (aggregated)
   - Include interfaces and routing tables per device

3. **Create links.json** — all inter-device connections

4. **Create vlans.json** — VLANs per site
   - Bangalore: VLANs 110, 120, 130, 420, 500, 600, 700
   - London/NYC: VLANs 110, 420, 500
   - Singapore: VLANs 110 (management), 200 (server)

5. **Create bgp_peers.json** — eBGP peering between all site edge routers

6. **Create services.json** — ERP, Auth, DB, Jira, Wiki, Monitoring (~6-8 services)

7. **Create user_groups.json** — One per VLAN per site

8. **Create telemetry_snapshot.json** — Static snapshot for key devices

9. **Implement TwinBuilder** (`twin/builder.py`)
   - Load all JSON files
   - Construct MultiDiGraph with all nodes and edges
   - Run validation

10. **Implement TwinManager** (`twin/manager.py`)
    - initialize(), clone_working(), reset()
    - baseline/working property access

11. **Implement Validator** (`twin/validator.py`)
    - Basic validation (required fields, cross-references)

### Acceptance Criteria

- [ ] All JSON files created with realistic data
- [ ] `TwinBuilder.build()` returns a valid MultiDiGraph
- [ ] Graph has correct node counts by type
- [ ] Graph has correct edge counts by relation
- [ ] All cross-references resolve (device IDs in links, VLANs, etc.)
- [ ] `TwinManager` can clone and reset working twin
- [ ] Unit tests for builder and manager pass

### Test

```python
def test_builder_loads_complete_graph():
    builder = TwinBuilder("network_state/")
    graph = builder.build()
    assert len([n for n, d in graph.nodes(data=True) if d["node_type"] == "site"]) == 4
    assert len([n for n, d in graph.nodes(data=True) if d["node_type"] == "device"]) >= 40
    # ... more assertions
```

---

## Phase 2: Graph Wrapper + Analysis Engine (Core)

**Goal**: Build the typed graph accessor and core analysis functions (path finding, blast radius).

### Tasks

1. **Implement GraphWrapper** (`twin/graph_wrapper.py`)
   - All methods from class hierarchy spec
   - Node/edge queries, typed convenience methods

2. **Implement path analysis** (`analysis/path.py`)
   - `trace_route()`: hop-by-hop using routing tables
   - `check_reachability()`: boolean reachability
   - `get_alternative_paths()`: all available paths
   - Source/destination resolution (user_group → device, service → device)

3. **Implement blast radius** (`analysis/blast_radius.py`)
   - `get_blast_radius()`: affected devices, services, users, severity
   - Severity calculation logic

4. **Implement topology queries** (`analysis/topology.py`)
   - `get_site_topology()`, `get_site_summary()`, `get_inter_site_connectivity()`
   - `search_devices()` with filters

5. **Implement comparison** (`analysis/comparison.py`)
   - `compare_with_baseline()`: diff working vs baseline

6. **Implement AnalysisEngine facade** (`analysis/engine.py`)

### Acceptance Criteria

- [ ] `trace_route("blr-corp-wifi-users", "erp-service")` returns valid hop-by-hop path
- [ ] `check_reachability()` returns true for connected components, false for disconnected
- [ ] `get_blast_radius("blr-core-01")` returns all downstream devices, services, users
- [ ] Severity calculation matches thresholds (critical >1000 users, etc.)
- [ ] `compare_with_baseline()` returns empty diff on fresh clone
- [ ] `search_devices(device_type="core_switch")` returns correct results
- [ ] All analysis functions are pure (no graph mutation)

### Key Design Decision — trace_route Algorithm

```
1. resolve_to_device(source) → src_device
2. resolve_to_prefix(destination) → dst_prefix
3. current = src_device, hops = []
4. while current != dst_device:
   a. Look up dst_prefix in current.routes
   b. If no matching route → unreachable, return failure
   c. next_hop = route.next_hop
   d. Check physical_link(current, next_hop) status == "up"
   e. If link down → unreachable at this hop
   f. Accumulate latency from link
   g. hops.append(current)
   h. current = next_hop
   i. Loop detection: if current in visited → routing loop
5. Return hops with latency
```

---

## Phase 3: Simulation Engine + Tools

**Goal**: Build mutation engine with cascading effects and wrap everything in agent-callable tools.

### Tasks

1. **Implement CascadingEffects** (`simulation/cascading.py`)
   - device_disabled / device_enabled
   - link_disabled / link_enabled
   - vlan_removed
   - bgp_peer_disabled / bgp_peer_enabled

2. **Implement SimulationEngine** (`simulation/engine.py`)
   - All mutation methods
   - Mutation logging

3. **Implement redundancy analysis** (`analysis/redundancy.py`)
   - `get_redundancy_status()`, `get_single_points_of_failure()`, `get_failover_path()`

4. **Implement ToolRegistry** (`tools/registry.py`)
   - Registration, lookup, execution

5. **Implement all 34 tools** (`tools/*.py`)
   - 21 query tools (exposed to agent) + 13 mutation tools (API-only)
   - Each tool delegates to simulation or analysis engine
   - Proper error handling

### Acceptance Criteria

- [ ] `disable_device("blr-core-01")` sets status to down AND disables all connected links
- [ ] `remove_vlan(420, "bangalore")` removes VLAN and returns affected user count (5000)
- [ ] `disable_bgp_peer(...)` withdraws prefixes and updates routing
- [ ] Cascading effects propagate correctly (device down → links down → services down)
- [ ] All 34 tools registered and callable through registry
- [ ] Only 21 query tools returned by `registry.list_agent_tools()`
- [ ] Tool execution returns structured dicts matching tool-schemas.md
- [ ] Mutation log tracks all changes
- [ ] `reset()` restores clean state

### Test — Cascading Effect

```python
def test_disable_device_cascades():
    sim.disable_device("blr-core-01")
    # Links should be down
    link = analysis.get_link_info("blr-core-01", "blr-edge-01")
    assert link["status"] == "down"
    # Service hosted on this device should be affected
    # ...
```

---

## Phase 4: Agent Implementation

**Goal**: Build the ReAct agent loop with LLM integration.

### Tasks

1. **Implement LLMProvider interface** (`agent/llm/base.py`)

2. **Implement OpenAI provider** (`agent/llm/openai_provider.py`)
   - Function calling API
   - Response parsing

3. **Implement Anthropic provider** (`agent/llm/anthropic_provider.py`)
   - Tool use API
   - Response parsing

4. **Write system prompt** (`agent/prompts/system_prompt.py`)
   - Role description
   - Tool descriptions (generated from registry)
   - Output format instructions
   - Investigation methodology guidance

5. **Implement ReactAgent** (`agent/react_agent.py`)
   - Core loop: thought → action → observation
   - Streaming events (AsyncGenerator)
   - Iteration limit
   - Error recovery (malformed LLM output)

6. **Implement agent event schemas** (`agent/schemas.py`)

### Acceptance Criteria

- [ ] Agent can complete Scenario 1 (VLAN 420 removal) end-to-end with mocked LLM
- [ ] Agent streams events (thought, tool_call, tool_result, final_answer)
- [ ] Agent stops after final_answer or MAX_ITERATIONS
- [ ] Malformed LLM response triggers retry (up to 3)
- [ ] System prompt includes all 21 query tool schemas (no mutation tools)
- [ ] Agent investigation is non-deterministic (LLM-driven, not hardcoded)

### Test — Mocked Agent Run

```python
async def test_agent_vlan_removal_scenario():
    # Pre-condition: remove VLAN 420
    sim.remove_vlan(420, "bangalore")
    
    # Mock LLM to return predetermined tool calls
    mock_llm = MockLLM(responses=[
        # Step 1: Check VLAN
        AgentResponse(thought="Check VLAN 420 status", action={"tool": "get_vlan_info", ...}),
        # Step 2: Get blast radius
        AgentResponse(thought="VLAN is missing, check impact", action={"tool": "get_blast_radius", ...}),
        # Step 3: Final answer
        AgentResponse(thought="Found root cause", action={"tool": "final_answer", ...})
    ])
    
    agent = ReactAgent(mock_llm, tool_registry, system_prompt)
    events = [e async for e in agent.run("WiFi users can't connect in Bangalore")]
    
    assert any(isinstance(e, FinalAnswerEvent) for e in events)
```

---

## Phase 5: API Layer

**Goal**: Expose backend via FastAPI with SSE streaming for the agent.

### Tasks

1. **Implement FastAPI app factory** (`api/app.py`)
   - Lifespan: initialize twin, engines, tools, agent
   - CORS configuration for frontend

2. **Implement agent endpoint** (`api/routes/agent.py`)
   - `POST /agent/query` → SSE stream of agent events

3. **Implement topology endpoints** (`api/routes/topology.py`)
   - `GET /topology/sites` → site list
   - `GET /topology/sites/{site}` → full site topology
   - `GET /topology/global` → inter-site view

4. **Implement simulation endpoints** (`api/routes/simulation.py`)
   - `POST /simulation/reset` → reset working twin
   - `POST /simulation/inject` → inject fault (calls simulation engine)

5. **Implement health endpoint** (`api/routes/health.py`)

6. **Implement Pydantic models** (`api/models.py`)

### Acceptance Criteria

- [ ] `GET /health` returns 200
- [ ] `GET /topology/sites` returns 4 sites
- [ ] `GET /topology/sites/bangalore` returns full topology
- [ ] `POST /simulation/inject` with disable_device returns cascading effects
- [ ] `POST /simulation/reset` restores clean state
- [ ] `POST /agent/query` streams SSE events
- [ ] CORS allows frontend origin
- [ ] Reset button disabled while agent is running (prevent state corruption)
- [ ] Only one agent query runs at a time (serialize requests)

---

## Phase 6: Frontend

**Goal**: Build React Flow topology visualization + agent chat panel.

### Tasks

1. **Project setup**: Next.js + Tailwind + shadcn/ui + React Flow

2. **Global topology view** (`GlobalView.tsx`)
   - Show 4 site nodes with WAN links between them
   - Color-coded health: 🟢 healthy, 🟡 degraded, 🔴 critical
   - Click site → drill into SiteView

3. **Site topology view** (`SiteView.tsx`)
   - React Flow graph of devices within a site
   - Different node shapes/icons per device type
   - Link status visualization (green=up, red=down, yellow=degraded)

4. **Device detail panel** (`DevicePanel.tsx`)
   - Sidebar showing device info, interfaces, routes, BGP state

5. **Agent chat panel** (`ChatPanel.tsx`)
   - Chat input
   - Display agent thoughts, tool calls, results, final answer
   - SSE consumption

6. **Fault injection panel** (`FaultPanel.tsx`)
   - Dropdown: select fault type
   - Parameter inputs (device, VLAN, link)
   - Inject button → calls simulation API

7. **Blast radius overlay** (`BlastOverlay.tsx`)
   - When blast radius computed, highlight affected nodes on topology
   - Red border on affected devices, orange on degraded

8. **API client** (`lib/api.ts`)
   - Fetch wrappers for all endpoints
   - SSE client for agent streaming

### Acceptance Criteria

- [ ] Global view shows 4 sites with health indicators
- [ ] Click site → shows internal topology
- [ ] Fault injection via UI updates topology colors
- [ ] Agent chat shows streaming thoughts and tool calls
- [ ] Blast radius highlights affected nodes on topology graph
- [ ] Responsive layout (sidebar + main view + chat)

---

## Phase 7: Demo Scenario Integration & Polish

**Goal**: End-to-end demo readiness for all 3 scenarios.

### Tasks

1. **Scenario 1 — VLAN 420 Removal**: Full walkthrough, verify agent output quality
2. **Scenario 2 — Leaf Switch Failure**: Full walkthrough
3. **Scenario 3 — WAN Link Degradation**: Full walkthrough
4. **System prompt tuning**: Adjust based on agent behavior in real scenarios
5. **UI polish**: Loading states, error handling, transitions
6. **README**: Setup instructions, architecture overview, demo guide

### Acceptance Criteria

- [ ] All 3 demo scenarios produce correct, insightful agent output
- [ ] Agent reasoning is visible and logical
- [ ] Blast radius visualization works for each scenario
- [ ] No crashes or errors during demo flow
- [ ] README covers setup and demo walkthrough
- [ ] Project runs from clean clone with documented steps

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| LLM tool selection errors | Good tool descriptions, few enough tools (35), system prompt tuning |
| Cascading effects bugs | Heavy unit testing in Phase 3, test each cascade path |
| trace_route complexity | Start with simple routing table lookup, iterate |
| React Flow performance | Aggregated devices keep node count <100 per site |
| LLM API costs during dev | Mock LLM provider for tests, real LLM only for integration |
| Time overrun | Phases 1-4 are the critical path. Phase 6 (frontend) can be simplified if needed |
