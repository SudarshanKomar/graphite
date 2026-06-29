# Specification Change Log

Cumulative log of all modifications made to spec files across audit rounds.

---

## Audit Round 1 — 2025-06-23

### `specs/adr/001-baseline-twin-architecture.md`
- **Change**: Replaced `get_diff()` with actual method names (`initialize()`, `clone_working()`, `reset()`, `baseline`, `working`)
- **Rationale**: `get_diff()` didn't exist in any implementation spec. Diff is on AnalysisEngine.

### `specs/adr/002-bgp-simulation-approach.md`
- **Change**: Renamed `bgp_peers` attribute reference to `bgp_state`
- **Rationale**: Graph schema uses `bgp_state`. Must be consistent.

### `specs/adr/003-agent-framework-selection.md`
- **Change**: Fixed tool registry path from `graphite/agent/tool_registry.py` to `graphite/tools/registry.py`
- **Rationale**: folder-structure.md and class-hierarchy.md both use `graphite/tools/registry.py`.

### `specs/adr/004-graph-representation.md`
- **Change**: Removed `bgp_peer` from edge key convention and DiGraph alternative examples. Added BGP-as-node-attribute note. Updated Multi justification to use `carries_vlan`.
- **Rationale**: bgp_peer edge type was removed per spec-refinements Issue 6 but ADR-004 was never updated.

### `specs/adr/005-tool-surface-consolidation.md`
- **Change**: Updated tool count from 35 to 34. Removed `get_bgp_summary` alias from BGP section. Added query/mutation split documentation.
- **Rationale**: Alias causes agent confusion (two names for same tool). Mutation tools shouldn't be agent-accessible.

### `specs/schemas/baseline-twin-json-schema.md`
- **Change**: Added validation rules 8-9 (unique IDs, interface references). Added "Builder Defaults" section documenting field renames and default values.
- **Rationale**: Duplicate IDs would cause graph construction errors. Field mapping from JSON to graph was undocumented.

### `specs/schemas/graph-node-edge-schema.md`
- **Change**: Updated MultiDiGraph justification to remove `bgp_peer` reference. Added BGP note.
- **Rationale**: Consistency with ADR-004 fix.

### `specs/schemas/tool-schemas.md`
- **Change**: (1) Added query/mutation classification header. (2) Removed `get_bgp_summary` alias. (3) Added `VlanAlreadyRemoved` error. (4) Added `DeviceDown` error to `enable_link`. (5) Added site health calculation rules. (6) Added scope filtering logic for `get_links`. (7) Updated tool summary to show 21 query + 13 mutation split.
- **Rationale**: Multiple gaps and edge cases identified during audit.

### `specs/implementation/folder-structure.md`
- **Change**: Removed `mutations.py` from simulation directory.
- **Rationale**: No classes or functions were defined for this file. All mutation logic is in `engine.py` + `cascading.py`.

### `specs/implementation/class-hierarchy.md`
- **Change**: (1) Added JSON-to-graph field mapping documentation to TwinBuilder. (2) Added `_recompute_service_health()` to SimulationEngine. (3) Added `category` field to ToolSchema. (4) Added `GlobalTopologyResponse` Pydantic model. (5) Added `site_name` and `user_groups` to SiteTopologyResponse.
- **Rationale**: Multiple gaps found during component-level and implementation-readiness audits.

### `specs/implementation/mvp-roadmap.md`
- **Change**: Updated tool count references (35→34, agent sees 21). Added concurrency/reset safety acceptance criteria.
- **Rationale**: Alignment with tool consolidation changes and edge case handling.

### `specs/implementation/spec-refinements.md`
- **Change**: Converted from unresolved issue tracker to resolved refinement history. Added ✅ status markers to all 10 issues. Updated summary table.
- **Rationale**: Per audit requirements — unresolved ambiguity must not remain.

### `specs/demo/demo-scenarios.md`
- **Change**: Fixed Scenario 1 VLAN removal description from "node removed from graph" to "node status set to removed". Fixed agent step 2 observation.
- **Rationale**: Contradiction with spec-refinements Issue 3 (VLAN node stays).

### `specs/frontend/frontend-architecture.md`
- **Change**: Updated SSE client comment from "Open EventSource" to "Use fetch() with POST + ReadableStream".
- **Rationale**: Contradiction with spec-refinements Issue 9 (EventSource only supports GET).

### New Files Created
- `specs/audit/audit-round-1-findings.md` — Audit findings document
- `specs/implementation/spec-change-log.md` — This file
