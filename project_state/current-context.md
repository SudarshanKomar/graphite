# Current Context

This file lets a future session quickly regain context. Read this first.

---

## Current Milestone

**Run 3 — Frontend + Real Gemini + E2E Demo + Product Polish** — complete.

Goal: make Graphite feel like a product. Validated real Gemini end-to-end, built the
Next.js operator console (topology-first + persistent copilot + fault simulation), added
the `/topology/global` endpoint, tuned prompts/loop, and ran full E2E validation.
Architecture frozen and preserved (twin model, GraphWrapper, query/mutation split, ReAct
agent, FastAPI structure, tool registry).

---

## Completed Work

### Run 1 — deterministic backend
- `network_state/` JSON source-of-truth; twin layer (`Validator`, `TwinBuilder`,
  `GraphWrapper`, `TwinManager`); analysis + simulation engines; 34-tool registry.
- pytest suite (66 tests).

### Run 2 — AI copilot
- `graphite/config.py`: pydantic-settings `Settings` + cached `get_settings()`
  (GEMINI_API_KEY, model/temperature, CORS origins, data path, agent max iterations).
- `graphite/agent/prompts/`: `build_system_prompt()` (tool catalogue + strict JSON
  contract + final_answer schema) and `format_observation/parse_retry/max_iterations`.
- `graphite/agent/parser.py`: robust JSON parsing (code fences, embedded objects).
- `graphite/agent/llm/`: `GeminiProvider.complete()` (async via `asyncio.to_thread`,
  lazy `google.generativeai`, system_instruction split, JSON mime) + `MockProvider`.
- `graphite/agent/react_agent.py`: full loop — message construction, parse + corrective
  retry, query-only tool enforcement, streaming `AgentEvent`s, `final_answer`/max-iter
  stopping, plus `investigate()` non-streaming convenience.
- `graphite/api/`: `create_app()` factory with lifespan-wired `Services` container,
  CORS, a `GraphiteError`->HTTP handler (404/409/400), and routers:
  health, topology, analysis, simulation (mutate/reset/diff/log), agent (`POST
  /agent/query`, SSE or non-streaming). Run with `python -m graphite.api`.
- Tests: `tests/test_agent.py` (11), `tests/test_api.py` (17) with mock LLM + TestClient.
- Live server smoke-tested end-to-end (health, sites, blast radius, mutate->diff->reset,
  503 when no LLM key).

---

## Run 3 additions

- Frontend `frontend/` (Next.js 16 + React 19 + Turbopack + Tailwind 3 + `@xyflow/react`
  v12 + Zustand). Three-panel console: LeftRail (sites/scenarios/faults), topology canvas
  (global + site, fault colors, blast overlay), Copilot (streaming ReAct). Lib layer:
  `api.ts`, `agentStream.ts` (SSE POST reader), `store.ts`, `types.ts`, layout/meta.
- Backend (additive/tuning): `/topology/global`; `GEMINI_API_KEY` alias fix; Gemini 429
  retry/translation; `agent_max_iterations` 15->10; VLAN node `id` exposed in inventory
  outputs + prompt hint so `get_blast_radius` resolves VLANs reliably.

## Active Blockers

- Gemini **free-tier quota** is the only blocker for live agent runs (per-minute and
  daily caps). Scenarios 1 & 2 validated live earlier in Run 3; the copilot surfaces 429s
  as clean error events. Deterministic flows (REST) are fully validated (6/6).
- IDE TS-server shows phantom `@/...`/`next` "cannot find module" errors because its root
  is the repo, not `frontend/`. `next build` + `tsc` are clean.

## How to run (Run 3)

- Backend: `cd backend && .venv/bin/python -m graphite.api` (binds `0.0.0.0:8000`).
- Frontend: `cd frontend && npm run dev` (`http://localhost:3000`, WSL-native Node v22).
- Node was installed non-root system-wide (`/usr/bin/node`); npm uses `strict-ssl false`
  for the corporate proxy. `frontend/.env.local` -> `NEXT_PUBLIC_API_BASE=http://localhost:8000`.

---

## V1 Released

V1 is complete, tagged, and frozen. All 3 runs delivered. Architecture preserved.

---

## V2 Implementation — MCP-Native Architecture

**Status**: All 6 phases complete. V2 migration finished.

### What Changed (Backend — Phases 1-5)
- **Phase 1**: Built `graphite/mcp/` package — `GraphiteMcpServer`, 36 tools, 6 resources,
  `CapabilityMode` (observe/operate).
- **Phase 2**: Migrated `ReactAgent` from `ToolRegistry` → `GraphiteMcpServer`.
- **Phase 3**: Rewired `Services`/`build_services`. Added `GET/POST /agent/mode`.
- **Phase 4**: Deleted `graphite/tools/` (V1 dead architecture removed).
- **Phase 5**: Created `graphite/mcp/__main__.py` (stdio) and `mcp.json` (Windsurf/WSL).

### What Changed (Frontend — Phase 6 + Refinement)
- **Observe/Operate mode UI**: Toggle badge in header (green=observe, amber=operate).
  Copilot header shows mode tag. Header border tints amber in operate mode.
- **Resizable panels**: Draggable separators between left rail ↔ canvas ↔ copilot.
  Min/max constraints (left 220-400px, right 300-600px). Smooth drag resize.
- **Responsive fixes**: Stats hide below `lg`, brand text hides below `sm`, AI/connection
  badges hide at narrow widths. No overflow/overlap at any practical width.
- **Panel sizing**: LeftRail and CopilotPanel fill parent container (no hardcoded widths).
- **V2 frontend spec**: Created `specs/v2/architecture/frontend-v2.md`.
- **MCP config**: `mcp.json` updated for Windows+WSL Windsurf configuration.

### V2.1 — Frontend Refinement + Localized Blast Radius
- **Blast card overlap fix**: CanvasOverlay restructured from separate absolute divs to a
  single flex-column container. Card flows below controls, no overlap at any width.
- **Separator rebound fix**: Root cause was stale closure capture in drag callbacks.
  Fixed by reading live width from `useStore.getState()` inside the handler. Added
  `minWidth`/`maxWidth` inline styles as CSS safety net.
- **Localized endpoint groups** (V2.1): Added `endpoint_groups.json` with 10 zone-level
  groups (floor-1 wireless, floor-1 wired, floor-1 voice, etc.). New `endpoint_group`
  graph node type with `serves_zone` edges from access devices. Blast radius now
  traverses these for localized impact.
  - TC1: `blr-ap-f1` → 625 users (was 0), severity high
  - TC2: `blr-access-f1` → 1,125 users (was 0), severity critical  
  - TC3: VLAN 420 removal → 5,000 users (no regression)
  - TC4: `sg-leaf-03` → 5 services affected (no regression)

### V2.1.1 — Endpoint Group Expansion + Device Breakdowns + Frontend Visibility
- **Endpoint groups expanded**: All office sites now have full coverage (BLR: 13 groups,
  LON: 6 groups, NYC: 4 groups = 23 total). Per-site endpoint-group user totals strictly
  match user-group totals (BLR=9500, LON=3000, NYC=2500). Parity enforced in builder.
- **Device breakdowns**: Each endpoint group has a `device_breakdown` field with realistic
  counts (smartphones, laptops, desktops, tablets, printers, IoT, VoIP/conf phones).
  Breakdown totals validated to match `estimated_users`.
- **Topology API**: `get_site_topology()` now returns `endpoint_groups` with device_breakdown
  and access_device info for frontend consumption.
- **Frontend user badges**: Access-layer devices (APs, access switches) that serve endpoint
  groups show a compact `👥 N users` badge. Clicking the badge expands an animated panel
  showing per-zone device breakdown (floor, device type counts).
- **Version**: Updated to v2.1.1 (pyproject.toml, FastAPI app, project state).
- **LON/NYC blast radius**: `lon-access-f1` → 1,000 users; `nyc-access-f1` → 1,250 users.

### Test Results
- Backend: 103 passed, 0 failed, 0 regressions
- Frontend: `next build` clean (TypeScript + compilation + 3 static pages)
- V2.1.1 validation: parity check + breakdown consistency + TC1-TC6 all passed

---

## Skill System (ADR-009)

- Added `.windsurf/rules/` with 3 always-on workspace rules (persona/grounding,
  response style, reasoning discipline) and `.windsurf/skills/` with 5 domain
  skills (failure-impact/blast-radius, redundancy/SPOF/recovery,
  service-dependency/root-cause, maintenance/change-planning,
  network-health/architecture-review). Auto-loaded by Windsurf on opening
  the repo; no code change, no new dependency. Targets the *external*
  MCP consumer path (Cascade connected via `python -m graphite.mcp`),
  complementing the internal ReAct agent's system prompt.
- Docs: `specs/v2/adr/009-skill-system.md` (decision) and
  `specs/v2/architecture/skill-system.md` (philosophy, per-skill
  rationale, extension guide).
- Purely additive — no changes to `graphite/agent/`, `graphite/mcp/`, or
  any test.

---

## Reasoning Architecture Redesign

Addressed a systemic issue where the agent reached conclusions too early
(1-3 tool calls for questions that need 10-25), then produced significantly
better answers when challenged by the user. Changes:

- **New rule `03-graphite-investigation-standards.md`** (keystone): depth
  classification, verification mandates (specific claims require specific
  tools), assumption audit, self-challenge protocol, common investigation
  failure patterns.
- **Rewritten rule `02`**: added pre-answer quality gate (5-point checklist).
- **Rewritten system prompt** (`system_prompt.py`): removed "be efficient —
  1 to 10 tool calls" which discouraged thorough investigation; added
  investigation discipline section with depth classification and
  verification mandates.
- **`agent_max_iterations` 10 → 25**: old value was tuned to the symptom
  (shallow 1-3 call investigations), not the desired behavior.
- **All 5 domain skills rewritten**: each now has mandatory evidence gates
  (tools that MUST be called), common trap warnings, and self-challenge
  requirements. Key additions: BGP topology verification for maintenance,
  cross-site reachability matrix, blast-radius + redundancy pairing.
- **Docs updated**: `specs/v2/architecture/skill-system.md`.

Test results: 109 passed, 0 failures (no regressions).

---

## Key Conventions To Preserve

- `GraphWrapper` is the ONLY module that imports `networkx`.
- Baseline twin is never mutated; mutations target the working twin.
- BGP state lives on device nodes as `bgp_state`, never as edges.
- Service health is recomputed after every mutation.
- Removed VLAN nodes remain in the graph with `status="removed"`.
