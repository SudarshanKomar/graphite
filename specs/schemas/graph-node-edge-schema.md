# Graph Node & Edge Schema

Complete specification of the NetworkX MultiDiGraph node types, edge types, and their attributes. This defines the in-memory representation after JSON is loaded.

---

## Graph Type

```python
import networkx as nx
G = nx.MultiDiGraph()
```

**MultiDiGraph** because:
- **Multi**: Parallel edges between same nodes (e.g., a device can have both `physical_link` and `carries_vlan` edges to the same neighbor)
- **Di**: Directed edges for asymmetric relations (`depends_on`, `hosted_on`)
- Bidirectional physical links are represented as two directed edges (A→B and B→A)

**Note**: BGP peering is stored as node attributes (`bgp_state`), NOT as graph edges. See ADR-004.

---

## Node Types

Every node has a `node_type` attribute. Queries filter by `node_type`.

### Site Node

Represents a geographic location / campus / datacenter.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `node_type` | `"site"` | yes | Fixed |
| `name` | string | yes | Full name (e.g., "Bangalore Campus") |
| `short_name` | string | yes | Short identifier |
| `location` | dict | yes | `{city, country}` |
| `as_number` | int | yes | BGP AS number |
| `prefix_block` | string | yes | Aggregate CIDR prefix |
| `employee_count` | int | yes | Approx employee count |

**Node ID format**: `site-{short_name}` → e.g., `site-bangalore`

### Device Node

Represents a network device (router, switch, firewall, server, AP).

| Attribute | Type | Required | Description |
|---|---|---|---|
| `node_type` | `"device"` | yes | Fixed |
| `name` | string | yes | Human name |
| `device_type` | string | yes | One of: `router`, `core_switch`, `distribution_switch`, `access_switch`, `leaf_switch`, `spine_switch`, `firewall`, `load_balancer`, `server`, `access_point` |
| `vendor` | string | yes | e.g., "Dell" |
| `model` | string | no | Model number |
| `os` | string | yes | e.g., "SONiC" |
| `site` | string | yes | Site short_name |
| `status` | string | yes | `"up"` or `"down"` |
| `management_ip` | string | no | Management IP |
| `role` | string | no | Free text |
| `interfaces` | list[dict] | yes | Interface list (see JSON schema) |
| `routes` | list[dict] | yes | Routing table (see JSON schema) |
| `bgp_state` | dict or None | no | BGP state (only on edge routers). Set during graph construction from `bgp_peers.json`. Contains `local_as`, `router_id`, `peers` list |
| `telemetry` | dict or None | no | Telemetry snapshot (if available) |

**Node ID format**: `{site_prefix}-{role}-{number}` → e.g., `blr-core-01`, `sg-leaf-03`

### VLAN Node

Represents a VLAN at a specific site.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `node_type` | `"vlan"` | yes | Fixed |
| `vlan_id` | int | yes | VLAN ID |
| `name` | string | yes | VLAN name |
| `subnet` | string | yes | IP subnet (CIDR) |
| `gateway` | string | yes | Default gateway IP |
| `site` | string | yes | Site short_name |
| `status` | string | yes | `"active"` or `"removed"`. Removed VLANs stay in graph for queryability |
| `description` | string | no | Description |

**Node ID format**: `{site_prefix}-vlan-{id}` → e.g., `blr-vlan-420`

### Service Node

Represents an application service.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `node_type` | `"service"` | yes | Fixed |
| `name` | string | yes | Human name |
| `service_type` | string | yes | e.g., `web_application`, `auth`, `database` |
| `site` | string | yes | Hosting site |
| `host_device` | string | yes | Device ID hosting service |
| `port` | int | no | Port number |
| `protocol` | string | no | Protocol |
| `status` | string | yes | `"healthy"`, `"degraded"`, `"down"` |
| `criticality` | string | yes | `"critical"`, `"high"`, `"medium"`, `"low"` |

**Node ID format**: `{service_id}` → e.g., `erp-service`

### User Group Node

Represents an aggregate user population on a VLAN.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `node_type` | `"user_group"` | yes | Fixed |
| `name` | string | yes | Group name |
| `site` | string | yes | Site short_name |
| `vlan_id` | int | yes | Associated VLAN ID |
| `estimated_users` | int | yes | User count |
| `device_types` | list[string] | no | Endpoint types |

**Node ID format**: `{group_id}` → e.g., `blr-corp-wifi-users`

---

## Edge Types

Every edge has a `relation` attribute used as the MultiDiGraph edge key. Each edge also carries type-specific attributes.

### physical_link

Physical network connection between devices.

| Direction | Bidirectional (A→B and B→A added) |
|---|---|
| From → To | device → device |

| Attribute | Type | Required | Description |
|---|---|---|---|
| `relation` | `"physical_link"` | yes | Edge key |
| `link_id` | string | yes | Unique link ID from JSON |
| `bandwidth` | string | yes | e.g., "100G" |
| `latency_ms` | float | yes | One-way latency (ms) |
| `link_type` | string | yes | `campus`, `datacenter`, `wan`, `mpls`, `vpn` |
| `status` | string | yes | `"up"` or `"down"` |
| `source_interface` | string | no | Interface name on source |
| `target_interface` | string | no | Interface name on target |

**Graph construction for bidirectional link**:
```python
attrs = {"relation": "physical_link", "link_id": link["id"], ...}
G.add_edge(link["source"], link["target"], key="physical_link", **attrs)
G.add_edge(link["target"], link["source"], key="physical_link", **attrs)
```

### belongs_to

Entity membership in a site.

| Direction | Directed (entity → site) |
|---|---|
| From → To | device/vlan/service/user_group → site |

| Attribute | Type | Required | Description |
|---|---|---|---|
| `relation` | `"belongs_to"` | yes | Edge key |

### carries_vlan

A device carries / trunks a VLAN.

| Direction | Directed (device → vlan) |
|---|---|
| From → To | device → vlan |

| Attribute | Type | Required | Description |
|---|---|---|---|
| `relation` | `"carries_vlan"` | yes | Edge key |

### serves

A VLAN provides network connectivity to a user group.

| Direction | Directed (vlan → user_group) |
|---|---|
| From → To | vlan → user_group |

| Attribute | Type | Required | Description |
|---|---|---|---|
| `relation` | `"serves"` | yes | Edge key |

### depends_on

Service dependency (directed acyclic in practice, but cycles allowed).

| Direction | Directed (dependent → dependency) |
|---|---|
| From → To | service → service |

| Attribute | Type | Required | Description |
|---|---|---|---|
| `relation` | `"depends_on"` | yes | Edge key |

### hosted_on

A service is hosted on a device.

| Direction | Directed (service → device) |
|---|---|
| From → To | service → device |

| Attribute | Type | Required | Description |
|---|---|---|---|
| `relation` | `"hosted_on"` | yes | Edge key |

---

## Edge Construction Rules

During graph build from JSON:

1. **Links** → `physical_link` edges (bidirectional pair)
2. **Devices** → `belongs_to` edge from device to its site
3. **VLANs** → `belongs_to` edge from VLAN to its site
4. **VLANs** → `carries_vlan` edge from each device in `vlan.devices[]` to the VLAN node
5. **Services** → `belongs_to` edge from service to its site
6. **Services** → `hosted_on` edge from service to its `host_device`
7. **Services** → `depends_on` edge from service to each service in `depends_on[]`
8. **User Groups** → `belongs_to` edge from user group to its site
9. **User Groups** → `serves` edge from the matching VLAN node to the user group

---

## Query Patterns

Common graph traversal patterns used by the analysis engine:

### Find all devices at a site
```python
[n for n in G.predecessors(f"site-{site}") 
 if G.nodes[n].get("node_type") == "device"]
```
Or more efficiently via the graph wrapper:
```python
graph.get_devices(site="bangalore")
```

### Find what a VLAN serves
```python
[n for _, n, d in G.out_edges(vlan_node_id, data=True) 
 if d.get("relation") == "serves"]
```

### Find all devices carrying a VLAN
```python
[n for n, _, d in G.in_edges(vlan_node_id, data=True)
 if d.get("relation") == "carries_vlan"]
```

### Find physical neighbors of a device
```python
[n for _, n, k in G.out_edges(device_id, keys=True)
 if k == "physical_link"]
```

### Find service dependency chain
```python
def get_dependency_chain(G, service_id, visited=None):
    if visited is None:
        visited = set()
    visited.add(service_id)
    deps = []
    for _, target, data in G.out_edges(service_id, data=True):
        if data.get("relation") == "depends_on" and target not in visited:
            deps.append(target)
            deps.extend(get_dependency_chain(G, target, visited))
    return deps
```

---

## Graph Invariants

The following must always hold:
1. Every node has a `node_type` attribute
2. Every edge has a `relation` attribute matching its key
3. Physical links always exist as bidirectional pairs (both removed/added together)
4. Every `belongs_to` edge points from a non-site node to a site node
5. `carries_vlan` always goes from a device to a VLAN
6. `serves` always goes from a VLAN to a user group
7. `depends_on` always goes between two services
8. `hosted_on` always goes from a service to a device
9. No orphan nodes (every node has at least one edge — enforced by `belongs_to`)
