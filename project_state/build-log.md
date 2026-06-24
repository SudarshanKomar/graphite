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
- Created `project_state/` tracking files.
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
