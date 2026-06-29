# Specification Refinements — Resolved History

All issues below were identified during Phase 2 self-review and have been **resolved** by updating the relevant spec files in-place. This file serves as an audit trail. No unresolved amendments remain.

---

## Issue 1: Blast Radius for Links (Edges vs Nodes)  
**Status: ✅ RESOLVED** — Applied to `tool-schemas.md`

**Problem**: `get_blast_radius` is documented as accepting "any node ID" but in Demo Scenario 3 it's called with a link_id (`link-blr-sg-wan`). Links are graph **edges**, not nodes.

**Resolution**: `get_blast_radius` accepts TWO formats:
1. **Node ID** (string): For devices, VLANs, services → e.g., `"blr-core-01"`, `"blr-vlan-420"`
2. **Link ID** (string): For links → e.g., `"link-blr-sg-wan"` — the tool resolves this to the corresponding edge using the `link_id` attribute stored on physical_link edges.

Updated parameter:
```
component_id: string (required) — Node ID or Link ID (from links.json)
```

The tool implementation checks: does a node with this ID exist? If not, search edges for `link_id` match. If neither found, raise ComponentNotFound.

---

## Issue 2: Service Health Derivation  
**Status: ✅ RESOLVED** — Applied to `class-hierarchy.md` (SimulationEngine._recompute_service_health)

**Problem**: No formal rules for when a service is `healthy`, `degraded`, or `down`.

**Resolution**: Add these rules to the simulation engine:

| Condition | Status |
|---|---|
| Host device is `down` | `down` |
| Host device is `up` but network path to host is broken | `down` |
| Host device is `up`, path exists, but ALL direct dependencies are `down` | `down` |
| Host device is `up`, path exists, SOME dependencies are `down`/`degraded` | `degraded` |
| Host device is `up`, path exists, all dependencies are `healthy` | `healthy` |

**Important**: Service health is **recomputed** after every mutation (part of cascading effects). The simulation engine calls `_recompute_service_health()` after each mutation completes.

---

## Issue 3: VLAN Removal — Node Stays in Graph  
**Status: ✅ RESOLVED** — Applied to `graph-node-edge-schema.md` (VLAN status attribute) and `demo-scenarios.md`

**Problem**: When `remove_vlan` is called, should the VLAN node be deleted from the graph or kept with `status="removed"`?

**Resolution**: Keep the node with `status="removed"`. 

Reasons:
- Agent can still query `get_vlan_info(420, "bangalore")` and get a meaningful response ("this VLAN was removed") instead of a confusing "not found"
- `compare_with_baseline()` can easily detect the change
- `get_blast_radius("blr-vlan-420")` still works on the node

What changes on removal:
- VLAN node attribute: `status` → `"removed"`
- All `carries_vlan` edges from devices to this VLAN: **removed** (devices no longer carry it)
- The `serves` edge from VLAN to user group: **removed** (users disconnected)
- The `belongs_to` edge: **kept** (VLAN still belongs to the site for query purposes)

On `add_vlan` (restoration): reverse the above.

---

## Issue 4: BGP Peer Cascading Must Be Reciprocal  
**Status: ✅ RESOLVED** — Applied to `tool-schemas.md` (disable_bgp_peer description)

**Problem**: When `disable_bgp_peer(device_id="blr-edge-01", peer_ip="10.99.14.2")` is called, the spec only discusses updating the local device's peer state. The remote device (sg-edge-01) should also see this peer as down.

**Resolution**: BGP peer disable is **always reciprocal**:
1. Local device: peer state → `idle`, prefixes from this peer withdrawn
2. Remote device: corresponding peer entry state → `idle`, prefixes from local device withdrawn
3. Both devices' routing tables updated accordingly

The simulation engine resolves `peer_ip` → `peer_device` and updates both sides.

Similarly, `enable_bgp_peer` restores both sides.

---

## Issue 5: trace_route Source/Destination Resolution  
**Status: ✅ RESOLVED** — Formal rules documented here; referenced by `tool-schemas.md`

**Problem**: The resolution logic for non-device sources/destinations is vague ("resolve to nearest access-layer device").

**Resolution**: Formal resolution rules:

### Source Resolution
| Source Type | Resolution |
|---|---|
| `device` | Use directly |
| `user_group` | Find the VLAN that serves this group (via `serves` edge). Find any `up` device that carries this VLAN (via `carries_vlan` edges). Pick the access-layer device (lowest in hierarchy). If multiple, pick first alphabetically (deterministic). |
| `vlan` | Resolve to the VLAN's gateway device. Find the device whose interface IP matches the VLAN's `gateway` attribute. |

### Destination Resolution
| Destination Type | Resolution |
|---|---|
| `device` | Use directly |
| `service` | Resolve to `host_device` attribute of the service |
| `subnet` (CIDR string like "10.50.0.0/14") | Find the device whose routing table has this as a `connected` route. If none, find the device at the destination site whose route table has a matching entry. |
| `user_group` | Same logic as source resolution |
| `vlan` | Same logic as source resolution |

### Routing Table Lookup (per hop)
At each hop, the algorithm does longest-prefix match on the destination prefix against the current device's routing table. If multiple matching routes exist, prefer:
1. Connected routes (metric 0)
2. Static routes (by metric)
3. BGP routes (by metric / AS path length)
4. If tie, pick first match (deterministic)

---

## Issue 6: Missing bgp_peer Edge Type in Graph Schema  
**Status: ✅ RESOLVED** — Applied to `graph-node-edge-schema.md` and `adr/004-graph-representation.md`

**Problem**: ADR-004 mentions `bgp_peer` as an example edge relation, but graph-node-edge-schema.md doesn't define it.

**Resolution**: BGP peering is stored **on device nodes** as attributes (bgp_state), NOT as graph edges.

Rationale: BGP is a control-plane relationship. The graph edges represent data-plane topology (can traffic flow?). BGP state determines which routes are available, but the BGP session itself travels over physical links. Adding bgp_peer edges would create redundancy with physical_link edges.

However, for the analysis engine to reason about BGP connectivity (e.g., "are these two edge routers BGP peers?"), it can check the `bgp_state` attribute on the device nodes. No separate edge type needed.

**Update to ADR-004**: Remove `bgp_peer` from the edge types discussion. It was listed as an example of why MultiDiGraph is needed (parallel edges), but the physical_link + carries_vlan between same devices is already sufficient justification.

---

## Issue 7: WAN Link Topology Between Sites  
**Status: ✅ RESOLVED** — Documented here; topology will be created in Phase 1 JSON data

**Problem**: Each site has 2 edge routers. How are they connected cross-site? Is it a full mesh or paired?

**Resolution**: **Paired active/active** design:
- `blr-edge-01` ↔ `lon-edge-01` (primary WAN link to London)
- `blr-edge-02` ↔ `lon-edge-02` (secondary WAN link to London)
- Same pattern for all site pairs that have direct WAN links

Not all sites are directly connected. WAN topology for MVP:
```
BLR ←→ LON  (2 redundant WAN links)
BLR ←→ SG   (2 redundant WAN links)
LON ←→ NYC  (2 redundant WAN links)
NYC ←→ SG   (2 redundant WAN links)
```

This gives every site at least 2 paths to every other site (direct + relay). Example: BLR→LON can go directly or BLR→SG→NYC→LON.

BGP enables path selection between these alternatives.

---

## Issue 8: Device Status vs Link Status Independence  
**Status: ✅ RESOLVED** — MVP simplification documented here

**Problem**: When a device is disabled then re-enabled, should links that were independently disabled (before device went down) remain disabled?

**Resolution for MVP**: **Simplify**. Device enable restores all links to their **baseline** state. Independent link disables are lost when device cycling happens. This is acceptable because:
1. The mutation log still records everything
2. In practice, demo scenarios don't combine device + link disables on the same device
3. Tracking per-link "disable reason" adds complexity with low value

If this becomes a problem, the fix is straightforward: add a `disable_reason` field to links (`"manual"` vs `"cascaded_from_device"`) and only restore cascaded links on device enable.

---

## Issue 9: Frontend SSE with POST  
**Status: ✅ RESOLVED** — Applied to `frontend-architecture.md` (SSE client section)

**Problem**: Standard SSE (EventSource API) only supports GET. Agent queries need POST (to send query body).

**Resolution**: Use **fetch API with ReadableStream**, not EventSource. This is the modern approach:

```typescript
const response = await fetch('/agent/query', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query: "..."})
});

const reader = response.body!.getReader();
const decoder = new TextDecoder();

while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    const text = decoder.decode(value);
    // Parse SSE format: "data: {...}\n\n"
    // Update state with parsed events
}
```

Backend uses FastAPI `StreamingResponse` with `media_type="text/event-stream"`.

---

## Issue 10: Access Switch Aggregation Clarification  
**Status: ✅ RESOLVED** — Documented here; consistent with ADR-004 device aggregation note

**Problem**: The spec says to aggregate access switches (e.g., `blr-access-f1` represents 8 switches). But device counts in user groups reference "5000 users on VLAN 420" — how does this work with aggregated switches?

**Resolution**: Aggregated access switch nodes represent a **floor's access layer** as a single logical device. They have:
- `device_type`: `access_switch`
- `name`: "BLR Floor 1 Access Layer" (not individual switch names)
- Interfaces: aggregated (a few representative trunk uplinks + aggregate access ports)
- The `estimated_users` on user groups is a separate count — it doesn't need to map 1:1 to device ports

For visualization and analysis, this abstraction is sufficient. The agent can say "10 access switch groups across 10 floors are affected" which is accurate enough for the demo.

---

## Summary of Phase 2 Amendments

All 10 issues identified during Phase 2 self-review have been resolved and applied to the relevant spec files.

| Issue | Status | Files Updated |
|---|---|---|
| 1. Blast radius for links | ✅ | tool-schemas.md |
| 2. Service health derivation | ✅ | class-hierarchy.md |
| 3. VLAN removal node behavior | ✅ | graph-node-edge-schema.md, demo-scenarios.md |
| 4. BGP reciprocal cascading | ✅ | tool-schemas.md |
| 5. trace_route resolution rules | ✅ | (documented in this file) |
| 6. bgp_peer edge type removal | ✅ | graph-node-edge-schema.md, ADR-004 |
| 7. WAN link topology | ✅ | (documented in this file) |
| 8. Device/link status independence | ✅ | (documented in this file) |
| 9. Frontend SSE with POST | ✅ | frontend-architecture.md |
| 10. Access switch aggregation | ✅ | (documented in this file, consistent with ADR-004) |
