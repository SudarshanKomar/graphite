# Architecture Deviations

Track any place where implementation differs from the specs. Each entry documents the
original spec, the actual implementation, the rationale, and the impact. This prevents
silent architecture drift.

If empty, implementation matches specs.

---

## D1: VLAN 420 subnet falls outside Bangalore aggregate prefix

- **Original spec:** Bangalore `prefix_block = 10.10.0.0/14` (ADR-002), while VLAN 420
  subnet is `10.42.0.0/16` and engineering VLAN 110 is `10.11.0.0/16`
  (baseline-twin-json-schema.md examples and demo-scenarios.md final answer).
  `10.42.0.0/16` is not contained within `10.10.0.0/14`.
- **Actual implementation:** Kept VLAN 420 subnet as `10.42.0.0/16` to match the demo
  scenario's expected agent output. The site `prefix_block` is used for BGP aggregate
  advertisement only and is not enforced to contain every VLAN subnet.
- **Rationale:** The demo scenario hardcodes these subnet values in the expected root
  cause. Fidelity to the demonstrable output outweighs strict CIDR containment in a
  simulation. No spec rule requires VLAN subnets to be within the site aggregate.
- **Impact:** Low. `trace_route`/reachability resolve destinations via routing tables and
  explicit subnet ownership, not by site-prefix containment, so behavior is unaffected.

---

## D2: LLM provider is Gemini, not OpenAI/Anthropic (spec default)

- **Original spec:** ADR-003 / class-hierarchy list `OpenAIProvider` (default) and
  `AnthropicProvider`.
- **Actual implementation (Run 2, done):** `GeminiProvider` (Gemini 2.5 Flash via
  `google.generativeai`) implements the `LLMProvider` protocol; a `MockProvider` provides
  deterministic offline/test responses. OpenAI/Anthropic remain valid future providers.
- **Rationale:** Explicit instruction for this project — an existing API key uses the
  Gemini package. Provider abstraction is preserved so models can be swapped later.
- **Impact:** Low. Only the concrete provider class changes; the agent loop and protocol
  are provider-agnostic. Status: RESOLVED (abstraction in place).

---

## D4: Service health follows the formal rules, not the demo narrative labels

- **Original spec (conflict):** `spec-refinements.md` Issue 2 (the authoritative health
  rules, applied to `class-hierarchy.md`) states: *host up, path exists, but ALL direct
  dependencies are down → `down`*. The `demo-scenarios.md` Scenario 2 narrative instead
  labels `auth-service` and `erp-service` as `degraded` when `db-cluster` is down.
- **Actual implementation:** `SimulationEngine._recompute_service_health()` follows the
  formal Issue 2 rules. With `db-cluster` down: `auth-service` (sole dep = db-cluster) →
  `down`; `erp-service` (deps auth + db, both down) → `down`; `monitoring-service`
  (no deps) → `healthy`.
- **Rationale:** The formal rule table is the precise implementation contract and is also
  more technically defensible (a service whose only datastore is down is not merely
  degraded). The demo narrative text is illustrative and was not reconciled with Issue 2
  during Audit Round 1.
- **Impact:** Medium for demo wording only. The deterministic output is correct and
  self-consistent. If the demo must read "degraded", change the rule to *some-or-all deps
  down → degraded*, but that weakens correctness. Flagged for a product decision.

---

## D5: Tool functions consolidated in the registry (Run 1)

- **Original spec:** `folder-structure.md` lists per-category tool modules
  (`device_tools.py`, `link_tools.py`, `vlan_tools.py`, …).
- **Actual implementation:** All 34 tools are defined as thin delegations in
  `tools/registry.py::build_default_registry`, with `tools/base.py` holding
  `ToolSchema`/`ToolContext`/`ToolRegistry`.
- **Rationale:** A single registry table is more maintainable for thin engine
  delegations and keeps the query/mutation contract in one place. The per-category
  split is cosmetic and can be done in Run 2 without changing the registry contract.
- **Impact:** None on behavior or the agent-facing tool surface.

---

## D3: Agent + API implemented (Run 2); Frontend still deferred

- **Original spec:** mvp-roadmap phases 4–6 cover agent, API, frontend.
- **Actual implementation:** Run 2 implements the ReAct agent, Gemini/Mock providers, and
  the FastAPI layer. Frontend (phase 6) remains deferred.
- **Rationale:** Run 1 was backend-only; Run 2 brings up the copilot + API. Frontend is a
  separate run.
- **Impact:** None on architecture; only the frontend layer is outstanding.

---

## D6: Extra `/analysis/*` REST routes beyond the four named groups

- **Original spec:** Run 2 instruction named health/topology/simulation/agent endpoints.
- **Actual implementation:** Added a read-only `/analysis/*` router (blast-radius, trace,
  reachability, spof, redundancy, service-dependencies) exposing existing AnalysisEngine
  methods directly to the frontend/clients.
- **Rationale:** These are pure read wrappers the UI and demos need; they add clear value
  without new logic and keep the agent's tools mirrored over HTTP.
- **Impact:** Additive only.

---

## D7: Single shared working twin across API requests

- **Original spec:** No explicit multi-tenant requirement.
- **Actual implementation:** One `Services` container (one working twin + one
  SimulationEngine with its mutation log) is shared by all requests. Simulation mutations
  are global until `POST /simulation/reset`.
- **Rationale:** Matches the single-operator demo model and keeps state simple.
- **Impact:** Concurrent users would share simulation state. Per-session isolation is
  listed as a Run 3 follow-up if needed.

---

## D8: Frontend uses `@xyflow/react` v12 + Next.js 16, not the spec's exact pins

- **Original spec:** `specs/frontend/frontend-architecture.md` lists Next.js 14, React
  Flow (the `reactflow` v11 package), shadcn/ui, and dagre layout.
- **Actual implementation:** Next.js 16.2.9 (Turbopack) + React 19, `@xyflow/react` v12
  (React Flow's current package), hand-rolled Tailwind primitives instead of the shadcn
  CLI, and a deterministic tiered layout instead of dagre. `next/font/google` was dropped
  in favor of system fonts.
- **Rationale:** The environment was prepared with Next 16 / React 19 / `@xyflow/react`
  v12 already installed; aligning to them avoided downgrade churn. Avoiding the shadcn CLI
  and Google font fetch sidesteps interactive/network steps that fail behind the TLS proxy.
  A tiered layout removes the dagre dependency and is fully deterministic for the demo.
- **Impact:** UI-layer only. Functionally matches the spec's three-panel, topology-first
  design and consumes the same REST + SSE contracts.

---

## D9: `/topology/global` endpoint added for the global map view

- **Original spec:** The frontend spec references `GET /topology/global`, which did not
  exist after Run 2 (only `/topology/sites` and per-site routes).
- **Actual implementation:** Added `GET /topology/global` returning sites (with health,
  device counts, users, normalized map positions) plus de-duplicated inter-site WAN links.
- **Rationale:** UI-driven additive endpoint (explicitly allowed in Run 3); composes
  existing AnalysisEngine queries, no new domain logic.
- **Impact:** Additive only.

---

## D10: VLAN inventory tools now expose the VLAN node `id`

- **Original spec:** `get_vlan_info`/`list_vlans` returned `vlan_id` (the numeric id) but
  not the internal graph node `id` (e.g. `blr-vlan-420`).
- **Actual implementation:** These tools (and `get_site_topology`) now also return `id`.
- **Rationale:** Real Gemini testing showed the agent could not feed `get_blast_radius`
  (which needs the node id) for VLANs, causing `ComponentNotFound` and a degraded answer.
  Exposing the id is the minimal root-cause fix and improved Scenario 1 correctness.
- **Impact:** Additive field; no breaking change to existing consumers.

---

## V2 Planned Architecture Changes (NOT YET IMPLEMENTED)

The following changes are specified in `specs/v2/` but have not been implemented. They are
documented here so future sessions understand the planned evolution.

- **ToolRegistry → MCP Server** (ADR-006): The custom `ToolRegistry` / `ToolSchema` /
  `ToolContext` abstraction will be replaced by a Graphite MCP Server. The agent becomes an
  MCP client. External agents gain access via stdio.
- **Query/mutation split → Capability modes** (ADR-007, revised): V1's hard split (agent
  sees only query tools) evolves to mode-based access. **Observe** mode (default, read-only)
  and **operate** mode (full topology control — destructive, restorative, analytical,
  remedial mutations). MCP server enforces modes at the protocol level.
- **LangChain** (ADR-008): Evaluated and rejected for V2. Custom ReAct agent preserved.

These are spec-phase decisions. No code has been modified. V1 architecture remains the
running implementation.

---

## D11: Gemini free-tier quota limits live agent testing

- **Context:** `gemini-2.5-flash` free tier enforces tight per-minute and daily request
  caps. Scenarios 1 & 2 were validated live; Scenario 3's full conclusion was 429-blocked.
- **Mitigation:** The provider translates 429s into a clear message and retries once
  (`llm_max_retries`, honoring the server-suggested delay). The copilot renders 429s as
  clean error events. Deterministic flows are validated without the LLM via REST (6/6).
- **Impact:** Operational only; not an architecture deviation. A higher-quota key removes
  the limit with no code change.
