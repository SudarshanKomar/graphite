# ADR-004: Graph Representation

**Status**: Accepted  
**Date**: 2025-06-22  
**Deciders**: Architecture Lead  

---

## Context

Networks are naturally graph-shaped. Graphite needs a graph representation that captures:
- Physical topology (devices, links)
- Logical topology (VLANs, subnets, user groups)
- Service dependencies
- Site hierarchy
- Enough metadata for routing, blast-radius, and troubleshooting analysis

## Decision

Use a **single heterogeneous NetworkX MultiDiGraph** containing both physical and logical entities.

### Why MultiDiGraph

| Requirement | Solution |
|---|---|
| Directed relationships (depends_on, hosted_on) | DiGraph |
| Bidirectional physical links | Add edge pairs (A→B and B→A) |
| Multiple edge types between same nodes | Multi (parallel edges with different keys) |
| Heterogeneous node types | Node attribute `node_type` |

### Why NOT Separate Physical/Logical Graphs

Initially considered: one physical graph, one logical graph. Rejected because:
- Cross-graph queries are complex ("which physical devices serve VLAN 420?")
- Synchronization between graphs on mutation is error-prone
- Blast radius naturally crosses physical/logical boundaries
- One graph with typed nodes/edges is simpler and equally expressive

### Node Types

Every node has a `node_type` attribute. All attributes below are stored as node attributes in the graph.

| Node Type | Key Attributes | Example ID |
|---|---|---|
| `site` | name, location, as_number, employee_count | `site-bangalore` |
| `device` | name, type, vendor, os, site, status, management_ip, interfaces, routes, bgp_state | `blr-core-01` |
| `vlan` | vlan_id, name, subnet, gateway, site | `blr-vlan-420` |
| `service` | name, type, site, host_device, port, status, criticality | `erp-service` |
| `user_group` | name, site, vlan_id, estimated_users, description | `blr-corp-wifi-users` |

**Note on device sub-types**: The `device` node has a `type` field that distinguishes router, core_switch, access_switch, leaf_switch, spine_switch, firewall, load_balancer, server, access_point.

**Note on interfaces**: Interfaces are NOT separate graph nodes. They are stored as a list attribute on device nodes. This avoids graph explosion (80 access switches × 48 ports = 3840 extra nodes). Interface info is accessed via `get_device_interfaces()` tool.

**Note on routing tables**: Stored as a `routes` attribute (list of route entries) on device nodes. Not graph edges. Forwarding path is computed at query time by the analysis engine traversing the graph and consulting route tables.

**Note on BGP state**: Stored as a `bgp_state` attribute on edge router nodes. Contains peers list with session state and prefix tables. See ADR-002.

### Edge Types

Every edge has a `relation` attribute (the edge key in MultiDiGraph).

| Relation | From → To | Directionality | Key Attributes |
|---|---|---|---|
| `physical_link` | device → device | Bidirectional (add both A→B, B→A) | bandwidth, latency_ms, link_type, status |
| `belongs_to` | device/vlan/service/user_group → site | Directed (entity → site) | — |
| `carries_vlan` | device → vlan | Directed | tagged (bool) |
| `serves` | vlan → user_group | Directed | — |
| `depends_on` | service → service | Directed | — |
| `hosted_on` | service → device | Directed | — |

### Edge Key Convention

In NetworkX MultiDiGraph, edges are identified by `(source, target, key)`. The `key` is the `relation` type. This allows multiple edges between the same pair of nodes (e.g., a device can have both a `physical_link` and a `carries_vlan` edge to the same neighbor, or two `physical_link` edges for redundant connections).

**Note on BGP**: BGP peering state is stored as **node attributes** (`bgp_state`) on edge router devices, NOT as graph edges. BGP is a control-plane relationship; the graph edges represent data-plane topology. See ADR-002.

### Bidirectional Physical Links

For every physical link, two directed edges are added:
```python
G.add_edge("blr-core-01", "blr-edge-01", key="physical_link", bandwidth="10G", latency_ms=1, status="up")
G.add_edge("blr-edge-01", "blr-core-01", key="physical_link", bandwidth="10G", latency_ms=1, status="up")
```

When disabling a link, **both directions** must be updated.

### Node ID Convention

Node IDs must be globally unique strings. Convention:

| Type | Pattern | Examples |
|---|---|---|
| Site | `site-{name}` | `site-bangalore`, `site-singapore` |
| Device | `{site_prefix}-{role}-{number}` | `blr-core-01`, `sg-leaf-03`, `lon-edge-01` |
| VLAN | `{site_prefix}-vlan-{id}` | `blr-vlan-420`, `sg-vlan-110` |
| Service | `{name}` | `erp-service`, `auth-service`, `db-cluster` |
| User Group | `{site_prefix}-{name}` | `blr-corp-wifi-users`, `blr-engineering-users` |

### Graph Scale Estimate

| Entity | Estimated Count |
|---|---|
| Sites | 4 |
| Devices | ~150–200 (routers, switches, servers, APs aggregated) |
| VLANs | ~25–30 (across all sites) |
| Services | ~8–10 |
| User Groups | ~15–20 |
| Physical Links | ~200–250 edges (×2 for bidirectional) |
| Other edges | ~100–150 |
| **Total nodes** | **~200–260** |
| **Total edges** | **~600–800** |

This is comfortably within NetworkX's in-memory performance. No need for Neo4j or specialized graph DB.

**Important note on device count**: We do NOT model all 80 access switches individually. For MVP, aggregate per floor or per distribution block. Example: `blr-access-f1` (floor 1 access layer, representing ~8 switches). This keeps the graph manageable for visualization while still being realistic. Detailed per-switch modeling can be a post-MVP enhancement.

## Consequences

**Positive:**
- Single graph handles all query types (physical, logical, service, blast-radius)
- NetworkX is well-documented, battle-tested, pure Python
- Heterogeneous typing via attributes is simple and flexible
- Graph size is trivial for in-memory processing

**Negative:**
- No graph query language (Cypher, SPARQL) — must write Python traversals
- Node type enforcement is by convention, not schema (no compile-time type safety)
- MultiDiGraph API is slightly more verbose than simple Graph

**Mitigation:**
- Wrap common queries in analysis engine functions
- Validate node types in TwinBuilder during construction
- Keep edge count manageable by aggregating access layer

## Alternatives Considered

### 1. Neo4j
Full graph database with Cypher. Rejected: adds infrastructure dependency, overkill for ~300 nodes, NetworkX is simpler for MVP.

### 2. Separate Physical + Logical Graphs
Two NetworkX graphs with cross-references. Rejected: see above (synchronization complexity, cross-graph queries).

### 3. NetworkX DiGraph (not Multi)
Single edge per node pair. Rejected: can't represent a `physical_link` AND a `carries_vlan` edge between the same device pair, or redundant parallel physical links.

### 4. NetworkX Graph (undirected)
Can't represent directed relationships (depends_on, hosted_on). Rejected.

## Implementation Notes

- Graph construction in `graphite/twin/builder.py`
- Graph wrapper with typed accessors in `graphite/twin/graph_wrapper.py`
- The wrapper provides methods like `get_devices(site=...)`, `get_neighbors(node_id, relation=...)`, `get_path(src, dst)` that abstract raw NetworkX API
- Node/edge validation during construction ensures required attributes are present
- `graph_wrapper.py` is the ONLY module that imports NetworkX directly — all other code goes through the wrapper
