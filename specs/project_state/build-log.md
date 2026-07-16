# Build Log

Chronological implementation journal. Newest entries at the bottom of each run.

---

## Run 1 — Core Backend Foundation

### Architecture understanding pass
- Read all ADRs (001–005), schemas (JSON, graph, tools), implementation docs
  (folder-structure, class-hierarchy, mvp-roadmap, spec-refinements, spec-change-log),
  audit findings, and demo scenarios.
- Confirmed core invariants and the query/mutation tool split.

### Scaffolding
- Created `specs/project_state/` tracking files.
- Created `backend/` with `pyproject.toml`, `requirements.txt`, `.env.example`,
  `.gitignore`, and the `graphite` package tree (twin/simulation/analysis/tools/agent/api).

### Data
- Authored `network_state/` JSON. Topology: BLR (campus), LON, NYC, SG (leaf-spine DC).
- WAN mesh: BLR-LON, BLR-SG, LON-NYC, NYC-SG (paired redundant edges per
  spec-refinements Issue 7).
- Designed data to support all 3 demo scenarios (VLAN 420 removal, sg-leaf-03 failure,
  BLR-SG WAN degradation).

### Twin layer
- `Validator`: required-field + cross-reference checks (rules 1–9 from JSON schema).
- `TwinBuilder`: JSON → MultiDiGraph with field renames (`type`→`device_type`/
  `service_type`), VLAN `status="active"` default, BGP/telemetry merge into device nodes.
- `GraphWrapper`: typed accessors; sole NetworkX importer.
- `TwinManager`: baseline build + working clone/reset.

### Analysis layer
- `path.py`: trace_route (routing-table hop-by-hop), check_reachability, alt paths,
  source/destination resolution per spec-refinements Issue 5.
- `blast_radius.py`: impact aggregation + severity thresholds.
- `redundancy.py`: redundancy status, SPOF (remove-and-test), failover path.
- `topology.py`: site topology/summary (+health rules), search_devices, inter-site.
- `comparison.py`: working-vs-baseline attribute diff.
- `engine.py`: AnalysisEngine facade.

### Simulation layer
- `cascading.py`: device/link/vlan/bgp cascade computations.
- `engine.py`: SimulationEngine mutation methods, MutationRecord log,
  `_recompute_service_health()` after each mutation, reset.

### Tools / agent
- `tools/registry.py` + `tools/base.py` (`ToolContext`, `ToolSchema`, `tool` decorator).
- Initial tool wrappers around analysis/simulation engines.
- Agent + LLM provider interfaces stubbed only (Run 1 scope).

### Tests
- pytest suite covering builder, graph wrapper, analysis, simulation, tools.
- Result: **66 passed**. Full-package import check passes (agent stubs do not import
  the Gemini SDK at module load).

### Demo-scenario verification (deterministic engine)
- **Scenario 1 (VLAN 420 removal):** blast radius = 5000 users / CRITICAL; node kept as
  `status=removed`; `blr-corp-wifi-users -> erp-service` becomes unreachable; baseline
  diff shows `vlan_removed`.
- **Scenario 2 (sg-leaf-03 down):** 3 links down; `db-cluster` down; `auth-service` and
  `erp-service` down per formal health rules (see deviation D4 — demo text says
  "degraded"); `monitoring-service` stays healthy; `sg-leaf-03` correctly flagged as a
  single point of failure.
- **Scenario 3 (BLR-SG latency 500ms):** `blr-corp-wifi-users -> erp-service` trace
  latency rises from ~56ms to ~501ms; `compare_with_baseline` reports `link_latency`.
- `reset()` returns a clean diff (0 mutations) in all cases.

### Environment
- Corporate TLS-intercepting proxy required `pip --trusted-host` to install deps.
- Dev versions: networkx 3.6, pytest 9 (API-compatible with pinned targets).

### Run 1 complete
- Deterministic backend foundation delivered: data + twin + graph + analysis +
  simulation + full tool surface + agent/LLM interface stubs + tests.

---

## Run 2 — AI Copilot (Agent + LLM + API)

### Config
- `graphite/config.py`: pydantic-settings `Settings` (env prefix `GRAPHITE_`, plus
  `GEMINI_API_KEY`), `data_path` resolution, `cors_origin_list`, `llm_configured`
  helper, and an `lru_cache`d `get_settings()`.

### Prompts
- `graphite/agent/prompts/`: `build_system_prompt(tools, max_iterations)` renders the
  query-tool catalogue, the strict single-JSON-object response contract, the
  `final_answer` schema, and operating rules. `templates.py` adds
  `format_observation`, `format_parse_retry`, and `format_max_iterations_notice`.

### LLM providers
- `GeminiProvider.complete()` — async (`asyncio.to_thread`), lazy `google.generativeai`
  import, splits system messages into `system_instruction`, maps assistant->model /
  tool->user roles, requests `application/json`. Returns raw text (agent owns parsing).
- `MockProvider` — scripted `responses` list or a `handler` callable; deterministic.

### Agent
- `parser.py`: `parse_agent_response()` recovers JSON from code fences / embedded
  objects and validates `thought` + `action{tool,parameters}`.
- `react_agent.py`: full loop — system+user message construction, LLM call with up to
  3 corrective parse retries, query-only tool enforcement (mutation/unknown tools are
  refused with a `ToolNotAvailable` observation), streamed events
  (thought/tool_call/tool_result/final_answer/error), and `final_answer` or
  max-iteration stopping with a forced-final fallback. `investigate()` returns the
  full trace non-streaming.

### API
- `graphite/api/`: `create_app()` factory wiring a shared `Services` container
  (twin/analysis/simulation/registry/provider) via lifespan + eager build, CORS, and a
  `GraphiteError`->HTTP handler (NotFound->404, InvalidMutation->409, else 400).
- Routers: `GET /health`, `/topology/*` (sites, site, summary, inter-site, device,
  search), `/analysis/*` (blast-radius, service-dependencies, trace, reachability,
  spof, redundancy), `/simulation/*` (mutate, reset, mutations, diff), and
  `POST /agent/query` (SSE stream or non-streaming). `python -m graphite.api` serves it.

### Tests
- `tests/test_agent.py` (11): parser cases, full VLAN-420 investigation, malformed-output
  recovery, parse-retry exhaustion -> error, mutation/unknown-tool refusal, domain-error
  surfacing, max-iteration stop.
- `tests/test_api.py` (17): health/root, topology + 404, analysis (blast-radius/trace/
  spof), simulation mutate->diff->reset, invalid type (400) / domain error (404) /
  invalid state (409), agent non-streaming + SSE + 503-without-LLM.
- Result: **94 passed**.

### Live verification
- Booted `python -m graphite.api` (port 8011) and curled: health (4 sites/40 devices),
  `/topology/sites`, `/analysis/blast-radius/blr-vlan-420` (CRITICAL), mutate
  `remove_vlan` (5000 users) -> `/simulation/diff` (`vlan_removed`) -> `/simulation/reset`
  (clean), and `/agent/query` returns 503 without a key. All as expected.

### Run 2 complete
- Copilot + API live on the deterministic backend. Frontend remains for a later run.

---

## Run 3 — Frontend + Real Gemini + E2E Demo + Product Polish

### Real Gemini validation
- Copied `.env.example` -> `.env`; fixed `Settings` so unprefixed `GEMINI_API_KEY` is read
  (`validation_alias` + `populate_by_name`). `llm_configured` -> true.
- Ran live investigations (gemini-2.5-flash):
  - Scenario 1 (remove VLAN 420): first attempt guessed a bad VLAN id and got
    `ComponentNotFound`. Root cause: inventory tools didn't expose the VLAN node `id`.
    Fix: return `id` from `get_vlan_info`/`list_vlans`/`get_site_topology` + a prompt hint.
    Re-run: `get_vlan_info` -> `get_blast_radius`, severity CRITICAL, 5000 users, ~11s.
  - Scenario 2 (disable sg-leaf-03): single `get_blast_radius`, CRITICAL, confidence 1.0,
    ~7s. Excellent tool selection.
  - Scenario 3 (BLR-SG 500ms): fault injected (`set_link_latency blr-edge-01/sg-edge-01`),
    first hop `get_inter_site_connectivity` correct; completion blocked by free-tier 429.
- Tuning: `agent_max_iterations` 15 -> 10 (runs use 1-3 calls); Gemini provider now
  translates 429s to a clear message and retries once honoring the server delay.

### Frontend (new) — Next.js operator console
- Toolchain reconciled to the prepared WSL env: Node v22 (`/usr/bin/node`), Next.js 16.2.9
  (Turbopack), React 19, `@xyflow/react` v12, Tailwind 3, Zustand. Removed the webpack
  block from `next.config.mjs` (Turbopack default); bumped React 18->19 and ESLint 8->9 to
  satisfy Next 16 peers; dropped `next/font/google` (proxy-safe system fonts).
- Lib: `types.ts` (backend-aligned), `api.ts` (REST), `agentStream.ts` (SSE via fetch +
  ReadableStream), `store.ts` (Zustand), `topologyLayout.ts`, `deviceMeta.ts`.
- UI: Header (brand + global status), LeftRail (SiteList, ScenarioBar, FaultPanel,
  ActiveFaults, DeviceDetail), TopologyCanvas (global site-map + tiered site view, fault
  coloring, blast-radius overlay + summary card, minimap), Copilot (streaming
  thoughts/tool-calls/results/final-answer, suggested prompts, stop). Premium graphite
  operator-console theme (subtle grid/glow, mono technical labels).
- Backend additive: `GET /topology/global` (sites + WAN links + map positions).

### Validation
- `next build` (Turbopack): compiled, TypeScript clean, 3 static pages.
- Backend `pytest`: 94 passed after Run 3 changes.
- E2E REST (`_e2e_check.py`, quota-safe): 6/6 — health, `/topology/global`, all 3 scenario
  mutate->blast/latency flows, reset-clears-faults.
- Both servers booted (api :8000, next :3000 -> 200); browser preview opened.

### Run 3 complete
- Topology-first console + persistent copilot + frictionless fault simulation, wired to the
  live backend. Architecture unchanged; all changes additive or tuning.

---

## V1 Released

V1 is complete and tagged. Runs 1–3 delivered the full stack: deterministic backend,
AI copilot, operator console, 3 validated demo scenarios.

---

## V2 Spec Phase — MCP-Native Architecture

### Context
- Architect evaluation suggested making Graphite consumable by external agents (IDE tools,
  Claude Desktop, enterprise orchestrators). MCP is the standard protocol for this.
- Also suggested evaluating LangChain as an agent framework alternative.

### Decisions made
- **ADR-006**: Replace custom `ToolRegistry` with a Graphite MCP Server. MCP becomes the
  canonical interface. ToolRegistry is removed (not wrapped).
- **ADR-007**: Replace V1's hard query/mutation split with capability modes
  (investigation/simulation). MCP server enforces mode-based access.
- **ADR-008**: LangChain formally evaluated. Conclusion: does not add value for Graphite V2.
  Custom ReAct agent preserved. One-axis-at-a-time principle (MCP first).

### V2 specs generated
- `specs/v1/README.md` — V1 spec archive index
- `specs/v2/README.md` — V2 overview and architecture diagram
- `specs/v2/adr/006-mcp-native-architecture.md` — MCP migration ADR
- `specs/v2/adr/007-capability-modes.md` — capability modes ADR
- `specs/v2/adr/008-langchain-evaluation.md` — LangChain evaluation ADR
- `specs/v2/architecture/mcp-server-design.md` — server structure, tools, resources, transport
- `specs/v2/architecture/mcp-tool-contracts.md` — all 36 tools with enriched descriptions
- `specs/v2/architecture/agent-mcp-integration.md` — agent migration (~30 lines changed)
- `specs/v2/architecture/safety-model.md` — 4-layer mutation defense
- `specs/v2/architecture/migration-plan.md` — 6-step plan, ~7-11 days, rollback strategy

### Design reasoning highlights
- **MCP primitives**: Tools (yes, all 34+2 meta), Resources (yes, 3 curated), Prompts (no —
  agents compose their own). Justified per-primitive, not blindly adopted.
- **In-process transport**: Internal ReAct agent calls MCP server methods directly (no
  serialization). External agents use stdio. SSE transport deferred.
- **Tool descriptions**: Enriched from 1-line V1 summaries to multi-sentence with parameter
  guidance, ID format examples, and severity threshold documentation.
- **Safety**: Investigation mode (default) → mutation refused at MCP server level. Simulation
  mode requires explicit opt-in. Defense-in-depth with system prompt + server enforcement.

### V2 spec phase complete
- No code changes in this phase. All 10 spec files delivered. Project state updated.
  Ready for V2 implementation.

---

## V2 Spec Revision — Architecture Corrections + Repo Cleanup + Roadmap

### Repo cleanup
- Moved all V1 spec directories (`adr/`, `audit/`, `demo/`, `frontend/`, `implementation/`,
  `schemas/`) from `specs/` root into `specs/v1/` via shell `mv`.
- Spec repo now has clean `specs/v1/` + `specs/v2/` structure with no root-level clutter.
- Updated all V2 cross-references to `specs/v1/` paths.

### Capability mode redesign (ADR-007 rewrite)
- **Old model**: investigation / simulation / remediation (phase-oriented, too narrow).
  Treated mutations only as fault injection. Wrong — mutations are general topology
  operations: destructive, restorative, analytical, remedial.
- **New model**: **observe** (read-only default) / **operate** (full topology control).
  Framed around agent autonomy level, not tool categories. Two modes is simpler and
  covers all V2 use cases (investigation, what-if, explicit mutation, remediation).
- Cascaded observe/operate naming through all V2 specs: ADR-007, safety model, tool
  contracts, agent integration, server design, migration plan, README.

### Consumer-aware behavior
- Added section to safety model documenting Graphite UI vs external IDE behavior.
- Graphite UI: agent can be concise (UI visualizes topology state).
- External IDE: agent responses must be self-contained (no visual context).
- No code branching needed — same MCP tool results, different system prompt guidance.

### Implementation roadmap (new)
- Created `specs/v2/implementation/v2-roadmap.md` — 6-phase plan with per-phase goals,
  modules, validation criteria, risks, and rollback strategy.
- Phases: MCP server → agent migration → app wiring → ToolRegistry removal →
  external agent (stdio) → frontend mode UI. Estimated ~7-11 days total.

### Audit fixes
- Fixed stale `mcp_client.py` reference in ADR-006 (agent calls server directly, no
  separate client module).
- Fixed tools/list contradiction: ADR-007 says tools are always listed (with annotations),
  but server design code was filtering. Fixed server design to match ADR-007.
- Fixed stale meta-tool description (still said "investigation/simulation").
- Fixed stale system prompt reference (still said "simulation mode").

### V2 spec revision complete
- No code changes. 12 spec files updated/created. Project state updated.

---

## V2 Implementation — MCP-Native Architecture (Phases 1–5)

### Phase 1 — MCP Server Foundation
- Created `graphite/mcp/` package: `mode.py` (CapabilityMode enum + state),
  `tools.py` (36 tool definitions with enriched multi-sentence descriptions),
  `resources.py` (6 resources — overview, 4 per-site, diff),
  `server.py` (GraphiteMcpServer — tool dispatch, mode enforcement, resources).
- Zero external dependencies (MCP SDK not needed for in-process path).
- Parity test: all 21 query tools produce identical results to V1 ToolRegistry.
- Mode enforcement validated: mutation refused in observe, allowed in operate.

### Phase 2 — Agent Migration
- `react_agent.py`: constructor takes `GraphiteMcpServer` instead of `ToolRegistry`.
  `_execute_tool` calls `mcp.call_tool()`. Agent-side query whitelist removed.
  `ModeViolation` exceptions surfaced as structured error observations.
- `prompts/system_prompt.py`: mode-aware prompt (OBSERVE vs OPERATE guidance blocks).
  Removed import of `ToolSchema`. Accepts duck-typed tool list.
- `prompts/templates.py`: `format_tool_catalog` supports both `ToolDef` and `ToolSchema`
  via duck typing (`input_schema` or `parameters`).
- `agent/llm/base.py`: `LLMProvider.complete()` tools param changed from
  `list[ToolSchema]` to `list` (generic). Decoupled from V1 tools package.

### Phase 3 — App Wiring + Mode API
- `api/state.py`: `Services.registry` → `Services.mcp_server`. `build_services`
  creates `GraphiteMcpServer`. `make_agent` passes MCP server.
- `api/routes/agent.py`: added `GET/POST /agent/mode` (observe/operate toggle).
- `api/routes/simulation.py`: mutation name lookup uses MCP server tool list.
- LLM providers (`mock_provider.py`, `gemini_provider.py`): removed `ToolSchema` imports.

### Phase 4 — Remove ToolRegistry
- Deleted `graphite/tools/` directory (base.py, registry.py, __init__.py).
- Confirmed zero remaining references (`grep` clean).
- `tests/conftest.py`: `registry` fixture → `mcp_server` fixture.
- `tests/test_tools.py`: fully rewritten for MCP server (tool counts, mode enforcement,
  resources, domain errors). 18 new tests.
- `tests/test_agent.py`: all `registry` → `mcp_server`. Mutation refusal test expects
  `ModeViolation` (not `ToolNotAvailable`).

### Phase 5 — External Agent Support (stdio)
- Created `graphite/mcp/__main__.py`: boots twin + engines + MCP server, wires to
  MCP SDK stdio transport. Clear error message if `mcp` package not installed.
- Created `mcp.json` at repo root for Claude Desktop / IDE configuration.
- The `mcp` SDK is not installed in the current environment (corporate proxy), so
  stdio transport is untested live. The in-process path (Phases 1-4) is fully validated.

### Validation
- **103 tests passed** (up from 94 in V1; +9 new MCP tests, -0 regressions).
- V1 ToolRegistry fully removed. Zero zombie architecture.
- Agent loop works end-to-end via MCP server with mock LLM.
- Mode enforcement (observe/operate) validated at MCP server level.
- All FastAPI endpoints work (health, topology, analysis, simulation, agent, mode).
