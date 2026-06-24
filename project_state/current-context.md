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

## Next Recommended Tasks (Run 4+)

1. Re-run all 3 scenarios live through the UI once Gemini quota resets (Scenario 3
   end-to-end conclusion was quota-blocked, not logic-blocked).
2. Optional: per-session working-twin isolation for concurrent users (today a single
   shared working twin is mutated by the simulation endpoints).
3. Optional polish: animate agent-driven path highlighting; persist conversation history;
   add a service-dependency inspector panel.

---

## Key Conventions To Preserve

- `GraphWrapper` is the ONLY module that imports `networkx`.
- Baseline twin is never mutated; mutations target the working twin.
- BGP state lives on device nodes as `bgp_state`, never as edges.
- Service health is recomputed after every mutation.
- Removed VLAN nodes remain in the graph with `status="removed"`.
