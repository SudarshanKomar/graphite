# Audit Round 1 — Findings

**Date**: 2025-06-23  
**Auditor**: Architecture Lead  
**Scope**: Full recursive audit of all 14 spec files (5 loops)

---

## Summary

- **Loops performed**: 5 (Global consistency → Component-level → Edge cases → Complexity reduction → Implementation readiness)
- **Total issues found**: 22
- **Critical issues**: 11 (all resolved)
- **Medium issues**: 8 (all resolved)
- **Low issues**: 3 (2 resolved, 1 accepted as-is)

---

## Critical Findings (Resolved)

### C1: ADR-004 stale `bgp_peer` edge reference
- **Severity**: Critical (contradiction)
- **Files**: `adr/004-graph-representation.md`
- **Problem**: Edge key convention and DiGraph alternative both referenced `bgp_peer` edge type, which was removed per spec-refinements Issue 6.
- **Resolution**: Updated to use `carries_vlan` as the parallel edge example. Added BGP-as-node-attribute note.

### C2: `bgp_peers` vs `bgp_state` naming inconsistency
- **Severity**: Critical (ambiguity)
- **Files**: `adr/002-bgp-simulation-approach.md` vs `schemas/graph-node-edge-schema.md`
- **Problem**: ADR-002 used `bgp_peers`, graph schema used `bgp_state` for the same attribute.
- **Resolution**: Standardized to `bgp_state` in ADR-002.

### C3: Wrong tool registry path in ADR-003
- **Severity**: Critical (incorrect reference)
- **Files**: `adr/003-agent-framework-selection.md`
- **Problem**: Said `graphite/agent/tool_registry.py`, should be `graphite/tools/registry.py`.
- **Resolution**: Fixed path.

### C4: Nonexistent `get_diff()` method in ADR-001
- **Severity**: Critical (missing interface)
- **Files**: `adr/001-baseline-twin-architecture.md`
- **Problem**: TwinManager listed `get_diff()` which doesn't exist in class hierarchy.
- **Resolution**: Replaced with actual method names and clarified diff is on AnalysisEngine.

### C5: Demo scenario contradicts VLAN removal behavior
- **Severity**: Critical (contradiction)
- **Files**: `demo/demo-scenarios.md`
- **Problem**: Said "node removed from graph" but spec-refinements Issue 3 established node stays with `status="removed"`.
- **Resolution**: Updated to "node status set to removed".

### C6: Frontend SSE client contradicts spec-refinements
- **Severity**: Critical (contradiction)
- **Files**: `frontend/frontend-architecture.md`
- **Problem**: Comment said "Open EventSource" but Issue 9 says fetch+ReadableStream.
- **Resolution**: Updated comment to reference fetch+ReadableStream.

### C7: JSON `type` → graph `device_type` mapping undocumented
- **Severity**: Critical (implementation ambiguity)
- **Files**: `schemas/baseline-twin-json-schema.md`, `implementation/class-hierarchy.md`
- **Problem**: JSON uses `type`, graph uses `device_type`. Builder must rename. Never documented.
- **Resolution**: Added explicit field mapping documentation to both TwinBuilder and JSON schema.

### C8: VLAN JSON missing `status` field → builder default undocumented
- **Severity**: Critical (implementation ambiguity)
- **Files**: `schemas/baseline-twin-json-schema.md`
- **Problem**: JSON has no `status` field but graph requires it.
- **Resolution**: Added "Builder Defaults" section documenting that `status="active"` is set during loading.

### C9: Mutation tools exposed to agent
- **Severity**: Critical (design flaw)
- **Files**: `schemas/tool-schemas.md`, `adr/005-tool-surface-consolidation.md`
- **Problem**: All 35 tools (including 13 mutation tools) were available to the agent. Agent could accidentally mutate state during investigation.
- **Resolution**: Split tools into query (21, agent-visible) and mutation (13, API-only). Added `category` field to ToolSchema. Updated all references.

### C10: `get_bgp_summary` alias creates confusion
- **Severity**: Critical (agent confusion)
- **Files**: `schemas/tool-schemas.md`, `adr/005-tool-surface-consolidation.md`
- **Problem**: Same tool listed under two names (`get_bgp_summary` and `get_device_bgp_summary`).
- **Resolution**: Removed alias. Single name: `get_device_bgp_summary`. Total tools: 34 (not 35).

### C11: Dead `mutations.py` in folder structure
- **Severity**: Critical (implementation confusion)
- **Files**: `implementation/folder-structure.md`
- **Problem**: Listed `mutations.py` but no class/function defined for it anywhere.
- **Resolution**: Removed from folder structure. All mutation logic is in `engine.py` + `cascading.py`.

---

## Medium Findings (Resolved)

### M1: Missing `GlobalTopologyResponse` schema
- **Files**: `implementation/class-hierarchy.md`
- **Resolution**: Added Pydantic model with `sites` and `wan_links` fields.

### M2: `VlanAlreadyRemoved` error case missing
- **Files**: `schemas/tool-schemas.md`
- **Resolution**: Added error case to `remove_vlan` tool.

### M3: Link enable should check device status
- **Files**: `schemas/tool-schemas.md`
- **Resolution**: Added `DeviceDown` error and note about device status check.

### M4: Missing duplicate ID validation rule
- **Files**: `schemas/baseline-twin-json-schema.md`
- **Resolution**: Added rule 8 (unique IDs) and rule 9 (interface connected_to references).

### M5: `get_site_summary` health calculation undefined
- **Files**: `schemas/tool-schemas.md`
- **Resolution**: Added formal health rules (healthy/degraded/critical).

### M6: `get_links` scope filtering logic undefined
- **Files**: `schemas/tool-schemas.md`
- **Resolution**: Added scope filtering logic section.

### M7: `_recompute_service_health()` missing from class hierarchy
- **Files**: `implementation/class-hierarchy.md`
- **Resolution**: Added method with formal rules.

### M8: Reset/concurrent safety undocumented
- **Files**: `implementation/mvp-roadmap.md`
- **Resolution**: Added acceptance criteria for reset-during-agent prevention and single-agent serialization.

---

## Low Findings

### L1: `SiteTopologyResponse` missing `user_groups` and `site_name` fields
- **Files**: `implementation/class-hierarchy.md`
- **Resolution**: Added fields to match `tool-schemas.md` output.

### L2: SPOF detection O(n²) performance
- **Status**: Accepted (not a problem for ~200 nodes)
- No action taken.

### L3: `prompts/` directory missing `__init__.py`
- **Status**: Accepted (Python 3 namespace packages don't require it; can be added during implementation)
- No action taken.

---

## Architecture Changes Made

### New: Query/Mutation Tool Split
The most significant architectural improvement. Tools are now categorized:
- **Query tools (21)**: Exposed to the agent via system prompt
- **Mutation tools (13)**: Available only through `POST /simulation/inject` API

This prevents the agent from accidentally mutating simulation state during investigation and reduces the agent's tool surface from 34 to 21, improving LLM tool selection accuracy.

### Removed: `get_bgp_summary` alias
Eliminates duplicate tool name confusion. BGP queries use `get_device_bgp_summary`.

### Removed: `mutations.py` from folder structure
Dead file with no defined content. All logic covered by `engine.py` + `cascading.py`.
