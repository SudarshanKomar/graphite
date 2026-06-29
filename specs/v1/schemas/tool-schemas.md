# Tool Schemas

Complete schema for all 34 agent tools. Each tool specifies: purpose, parameters, return type, error cases, and which engine it delegates to.

**Convention**: Mutation tools go through the **Simulation Engine**. Query tools go through the **Analysis Engine**. Both operate on the working twin graph.

**Agent Access**: The agent's system prompt only includes **query tools** (21 tools). Mutation tools are NOT exposed to the agent — they are invoked only through the `POST /simulation/inject` API endpoint (frontend fault injection panel). This prevents the agent from accidentally mutating state during investigation.

Tools are tagged in the registry as `category: "query"` or `category: "mutation"`.

---

## 1. Device Management

### get_device_info

Returns metadata and current status for a device.

```
Parameters:
  device_id: string (required) — Device ID (e.g., "blr-core-01")

Returns: {
    id: string,
    name: string,
    device_type: string,
    vendor: string,
    model: string | null,
    os: string,
    site: string,
    status: "up" | "down",
    management_ip: string | null,
    role: string | null
}

Errors:
  - DeviceNotFound: "Device '{device_id}' not found"

Engine: Analysis
```

### get_device_interfaces

Returns all interfaces on a device with their status, IPs, VLANs.

```
Parameters:
  device_id: string (required)

Returns: {
    device_id: string,
    interfaces: [
        {
            name: string,
            ip_address: string | null,
            status: "up" | "down",
            speed: string | null,
            connected_to: string | null,
            vlan_mode: "access" | "trunk" | null,
            allowed_vlans: [int] | null,
            access_vlan: int | null
        }
    ]
}

Errors:
  - DeviceNotFound

Engine: Analysis
```

### get_device_routes

Returns the routing table for a device.

```
Parameters:
  device_id: string (required)

Returns: {
    device_id: string,
    routes: [
        {
            prefix: string,
            next_hop: string,
            next_hop_ip: string | null,
            protocol: "static" | "connected" | "bgp" | "ospf",
            metric: int | null,
            status: "active" | "inactive"
        }
    ]
}

Errors:
  - DeviceNotFound

Engine: Analysis
```

### get_device_bgp_summary

Returns BGP state for a device (peers, session state, prefixes).

```
Parameters:
  device_id: string (required)

Returns: {
    device_id: string,
    local_as: int,
    router_id: string,
    peers: [
        {
            peer_ip: string,
            peer_device: string,
            peer_as: int,
            state: "established" | "idle" | "active",
            prefixes_received: [string],
            prefixes_advertised: [string]
        }
    ]
} | null  (null if device has no BGP config)

Errors:
  - DeviceNotFound

Engine: Analysis
```

### disable_device

Marks a device as down. Cascading effects: all physical links on this device go down, VLANs that relied solely on this device become unreachable, services hosted on this device go down.

```
Parameters:
  device_id: string (required)

Returns: {
    device_id: string,
    previous_status: "up",
    new_status: "down",
    cascading_effects: {
        links_disabled: [string],        — link IDs
        services_affected: [string],     — service IDs
        vlans_affected: [string],        — VLAN node IDs
        bgp_peers_dropped: [string]      — peer descriptions
    }
}

Errors:
  - DeviceNotFound
  - DeviceAlreadyDown: "Device '{device_id}' is already down"

Engine: Simulation
```

### enable_device

Marks a device as up. Restores links, re-establishes BGP peers, restores services.

```
Parameters:
  device_id: string (required)

Returns: {
    device_id: string,
    previous_status: "down",
    new_status: "up",
    restored: {
        links_restored: [string],
        services_restored: [string],
        bgp_peers_restored: [string]
    }
}

Errors:
  - DeviceNotFound
  - DeviceAlreadyUp

Engine: Simulation
```

---

## 2. Link Management

### get_link_info

Returns details for a specific link between two devices.

```
Parameters:
  source: string (required) — Source device ID
  target: string (required) — Target device ID

Returns: {
    link_id: string,
    source: string,
    target: string,
    bandwidth: string,
    latency_ms: float,
    link_type: string,
    status: "up" | "down"
}

Errors:
  - LinkNotFound: "No link between '{source}' and '{target}'"

Engine: Analysis
```

### get_links

Returns links filtered by scope.

```
Parameters:
  scope: "site" | "wan" | "all" (required)
  site: string (optional) — Required when scope="site"

Returns: {
    scope: string,
    site: string | null,
    links: [
        {
            link_id: string,
            source: string,
            target: string,
            bandwidth: string,
            latency_ms: float,
            link_type: string,
            status: "up" | "down"
        }
    ]
}

Errors:
  - SiteNotFound (when scope="site" and site doesn't exist)
  - MissingSite: "Parameter 'site' required when scope='site'"

Engine: Analysis
```

**Scope filtering logic**:
- `scope="site"`: Return links where BOTH source and target devices belong to the specified site
- `scope="wan"`: Return links with `link_type` in (`wan`, `mpls`, `vpn`)
- `scope="all"`: Return all links in the graph

### disable_link

Marks a link as down (both directions). Cascading: if this was the only path between two segments, those segments become unreachable.

```
Parameters:
  source: string (required)
  target: string (required)

Returns: {
    link_id: string,
    previous_status: "up",
    new_status: "down",
    cascading_effects: {
        segments_isolated: [string],     — device IDs that lost connectivity
        alternative_paths_available: bool
    }
}

Errors:
  - LinkNotFound
  - LinkAlreadyDown

Engine: Simulation
```

### enable_link

Restores a link (both directions).

```
Parameters:
  source: string (required)
  target: string (required)

Returns: {
    link_id: string,
    previous_status: "down",
    new_status: "up",
    restored: {
        connectivity_restored_to: [string]
    }
}

Errors:
  - LinkNotFound
  - LinkAlreadyUp
  - DeviceDown: "Cannot enable link — device '{device_id}' is down"

Engine: Simulation

Note: If either endpoint device is down, the link cannot be enabled. The device must be brought up first.
```

### set_link_latency

Changes the latency of a link. Used to simulate WAN degradation.

```
Parameters:
  source: string (required)
  target: string (required)
  latency_ms: float (required) — New latency in milliseconds

Returns: {
    link_id: string,
    previous_latency_ms: float,
    new_latency_ms: float,
    affected_paths: int — Count of paths that traverse this link
}

Errors:
  - LinkNotFound
  - InvalidLatency: "Latency must be positive"

Engine: Simulation
```

---

## 3. VLAN Management

### get_vlan_info

Returns VLAN details including devices carrying it and estimated user count.

```
Parameters:
  vlan_id: int (required)
  site: string (required)

Returns: {
    vlan_id: int,
    name: string,
    subnet: string,
    gateway: string,
    site: string,
    status: "active" | "removed",
    devices: [string],
    user_groups: [
        {
            id: string,
            name: string,
            estimated_users: int
        }
    ],
    total_estimated_users: int
}

Errors:
  - VlanNotFound: "VLAN {vlan_id} not found at site '{site}'"

Engine: Analysis
```

### list_vlans

Returns all VLANs at a site.

```
Parameters:
  site: string (required)

Returns: {
    site: string,
    vlans: [
        {
            vlan_id: int,
            name: string,
            subnet: string,
            status: "active" | "removed"
        }
    ]
}

Errors:
  - SiteNotFound

Engine: Analysis
```

### add_vlan

Adds a VLAN to a site. Used for remediation.

```
Parameters:
  vlan_id: int (required)
  site: string (required)
  subnet: string (required) — CIDR notation
  name: string (required)
  devices: [string] (required) — Device IDs to carry this VLAN

Returns: {
    vlan_node_id: string,
    vlan_id: int,
    site: string,
    devices_configured: [string],
    connectivity_restored_to: [string] — User groups that regained access
}

Errors:
  - SiteNotFound
  - VlanAlreadyExists
  - DeviceNotFound (for any device in devices list)

Engine: Simulation
```

### remove_vlan

Removes a VLAN from a site. Cascading: user groups lose connectivity, services accessed through this VLAN become unreachable for those users.

```
Parameters:
  vlan_id: int (required)
  site: string (required)

Returns: {
    vlan_node_id: string,
    vlan_id: int,
    site: string,
    cascading_effects: {
        devices_unconfigured: [string],
        user_groups_disconnected: [
            {
                id: string,
                name: string,
                estimated_users: int
            }
        ],
        total_users_affected: int,
        services_impacted: [string] — Services that became unreachable for disconnected users
    }
}

Errors:
  - VlanNotFound
  - VlanAlreadyRemoved: "VLAN {vlan_id} at site '{site}' is already removed"

Engine: Simulation
```

---

## 4. Routing & Path

### trace_route

Simulated traceroute from source to destination. Returns each hop with latency. Follows routing tables hop-by-hop.

```
Parameters:
  source: string (required) — Device ID, VLAN ID, or user group ID
  destination: string (required) — Device ID, service ID, or subnet (CIDR)

Returns: {
    source: string,
    destination: string,
    reachable: bool,
    hops: [
        {
            hop_number: int,
            device_id: string,
            device_name: string,
            latency_ms: float — Cumulative latency to this hop
        }
    ],
    total_latency_ms: float,
    total_hops: int,
    failure_point: string | null — Device ID where path breaks (if unreachable)
}

Errors:
  - NodeNotFound: "Source '{source}' not found"
  - NodeNotFound: "Destination '{destination}' not found"

Engine: Analysis
```

**Source resolution**: If source is a user_group, resolve to the nearest access-layer device. If source is a VLAN, resolve to the gateway device.

**Destination resolution**: If destination is a service, resolve to its host_device. If destination is a subnet (CIDR), find the device that owns that prefix.

### check_reachability

Boolean reachability check. Faster than trace_route (early termination).

```
Parameters:
  source: string (required)
  destination: string (required)

Returns: {
    source: string,
    destination: string,
    reachable: bool,
    path: [string] | null — Device IDs in path (if reachable)
    failure_reason: string | null — Human-readable reason (if unreachable)
}

Engine: Analysis
```

### get_alternative_paths

Returns all available paths (ECMP, redundant) between source and destination.

```
Parameters:
  source: string (required) — Device ID
  destination: string (required) — Device ID

Returns: {
    source: string,
    destination: string,
    paths: [
        {
            path: [string],
            total_latency_ms: float,
            total_hops: int,
            is_active: bool — Currently used for forwarding
        }
    ],
    ecmp_available: bool,
    total_paths: int
}

Errors:
  - NodeNotFound

Engine: Analysis
```

### add_static_route

Adds a static route to a device's routing table.

```
Parameters:
  device_id: string (required)
  prefix: string (required) — CIDR
  next_hop: string (required) — Next hop device ID

Returns: {
    device_id: string,
    route_added: {prefix: string, next_hop: string, protocol: "static"},
    reachability_changes: [string] — Destinations now reachable via this route
}

Errors:
  - DeviceNotFound
  - RouteConflict: "Route to {prefix} already exists"
  - InvalidNextHop: "Next hop '{next_hop}' not directly connected"

Engine: Simulation
```

### remove_static_route

Removes a static route from a device's routing table.

```
Parameters:
  device_id: string (required)
  prefix: string (required) — CIDR

Returns: {
    device_id: string,
    route_removed: {prefix: string, next_hop: string},
    reachability_changes: [string] — Destinations that may have lost reachability
}

Errors:
  - DeviceNotFound
  - RouteNotFound

Engine: Simulation
```

---

## 5. BGP

### disable_bgp_peer

Disables a BGP peer session. Cascading: prefixes withdrawn, routes recalculated. **Reciprocal**: the remote device's corresponding peer entry is also set to `idle` and its prefixes from the local device are withdrawn.

```
Parameters:
  device_id: string (required)
  peer_ip: string (required)

Returns: {
    device_id: string,
    peer_ip: string,
    peer_as: int,
    previous_state: "established",
    new_state: "idle",
    cascading_effects: {
        prefixes_withdrawn: [string],
        routes_removed: int,
        destinations_unreachable: [string] — Prefixes that lost all paths
    }
}

Errors:
  - DeviceNotFound
  - PeerNotFound: "No BGP peer {peer_ip} on device '{device_id}'"
  - PeerAlreadyDown

Engine: Simulation
```

### enable_bgp_peer

Re-enables a BGP peer session. Restores prefix advertisement.

```
Parameters:
  device_id: string (required)
  peer_ip: string (required)

Returns: {
    device_id: string,
    peer_ip: string,
    new_state: "established",
    restored: {
        prefixes_received: [string],
        prefixes_advertised: [string],
        routes_added: int
    }
}

Errors:
  - DeviceNotFound
  - PeerNotFound
  - PeerAlreadyUp

Engine: Simulation
```

### withdraw_prefix

Withdraws a specific prefix from a device's BGP advertisements.

```
Parameters:
  device_id: string (required)
  prefix: string (required) — CIDR

Returns: {
    device_id: string,
    prefix: string,
    peers_notified: [string],
    cascading_effects: {
        destinations_affected: [string]
    }
}

Errors:
  - DeviceNotFound
  - PrefixNotFound

Engine: Simulation
```

### advertise_prefix

Advertises a new prefix from a device.

```
Parameters:
  device_id: string (required)
  prefix: string (required) — CIDR

Returns: {
    device_id: string,
    prefix: string,
    peers_notified: [string],
    reachability_restored: [string]
}

Errors:
  - DeviceNotFound
  - PrefixAlreadyAdvertised

Engine: Simulation
```

---

## 6. Impact Analysis

### get_blast_radius

Core analysis tool. Returns full impact assessment for a failed or removed component. Works on any component type (device, VLAN, link, service).

```
Parameters:
  component_id: string (required) — Node ID (device, VLAN, service) OR Link ID
      from links.json (e.g., "link-blr-sg-wan"). For links (which are graph edges,
      not nodes), the tool resolves the link_id to the corresponding edge.

Returns: {
    component_id: string,
    component_type: string,
    status: string,
    affected_devices: [
        {
            id: string,
            name: string,
            impact: "down" | "degraded" | "isolated"
        }
    ],
    affected_services: [
        {
            id: string,
            name: string,
            impact: "down" | "degraded",
            reason: string
        }
    ],
    affected_user_groups: [
        {
            id: string,
            name: string,
            estimated_users: int,
            impact: "disconnected" | "degraded"
        }
    ],
    total_users_affected: int,
    severity: "critical" | "high" | "medium" | "low",
    severity_factors: [string] — Reasons for severity rating
}

Errors:
  - ComponentNotFound

Engine: Analysis
```

**Severity calculation**:
- **critical**: >1000 users affected OR any critical service down
- **high**: >100 users OR high-criticality service affected
- **medium**: >10 users OR medium-criticality service affected
- **low**: <10 users, no critical services

### get_service_dependencies

Returns the dependency graph for a service (full chain).

```
Parameters:
  service_id: string (required)

Returns: {
    service_id: string,
    service_name: string,
    status: "healthy" | "degraded" | "down",
    host_device: string,
    host_device_status: string,
    site: string,
    direct_dependencies: [
        {
            id: string,
            name: string,
            status: string
        }
    ],
    transitive_dependencies: [
        {
            id: string,
            name: string,
            status: string,
            depth: int — How many hops from the queried service
        }
    ],
    dependent_services: [
        {
            id: string,
            name: string — Services that depend ON this service
        }
    ]
}

Errors:
  - ServiceNotFound

Engine: Analysis
```

---

## 7. Redundancy Analysis

### get_redundancy_status

Checks if a component has redundant/backup paths or failover capability.

```
Parameters:
  component_id: string (required) — Device ID or link ID

Returns: {
    component_id: string,
    component_type: string,
    has_redundancy: bool,
    redundancy_details: {
        parallel_links: int,
        alternative_paths: int,
        failover_available: bool,
        ecmp_enabled: bool
    },
    risk_assessment: "no_risk" | "low_risk" | "single_point_of_failure"
}

Errors:
  - ComponentNotFound

Engine: Analysis
```

### get_single_points_of_failure

Returns all single points of failure for a site.

```
Parameters:
  site: string (required)

Returns: {
    site: string,
    single_points_of_failure: [
        {
            component_id: string,
            component_type: string,
            failure_impact: string — Brief description of what breaks
        }
    ],
    total_spofs: int,
    risk_level: "low" | "medium" | "high"
}

Errors:
  - SiteNotFound

Engine: Analysis
```

### get_failover_path

When a primary component fails, returns the failover path.

```
Parameters:
  primary_component: string (required) — Device ID or link (as "source:target")

Returns: {
    primary_component: string,
    failover_available: bool,
    failover_path: [string] | null,
    failover_latency_ms: float | null,
    latency_increase_ms: float | null — vs primary path
}

Errors:
  - ComponentNotFound

Engine: Analysis
```

---

## 8. Topology & Discovery

### get_site_topology

Returns the full topology of a site: devices, links, VLANs, services.

```
Parameters:
  site: string (required)

Returns: {
    site: string,
    site_name: string,
    devices: [{id, name, device_type, status}],
    links: [{source, target, bandwidth, latency_ms, status}],
    vlans: [{vlan_id, name, subnet, status}],
    services: [{id, name, status, criticality}],
    user_groups: [{id, name, estimated_users}]
}

Errors:
  - SiteNotFound

Engine: Analysis
```

### get_site_summary

High-level site stats.

```
Parameters:
  site: string (required)

Returns: {
    site: string,
    device_count: int,
    devices_up: int,
    devices_down: int,
    link_count: int,
    links_up: int,
    links_down: int,
    vlan_count: int,
    service_count: int,
    total_users: int,
    health: "healthy" | "degraded" | "critical"
}

Errors:
  - SiteNotFound

Engine: Analysis
```

**Site health calculation**:
- **healthy**: All devices up AND all links up
- **degraded**: Any device or link down, but edge routers and core switches are up
- **critical**: Any edge router or core switch down, OR >50% of devices down

### get_inter_site_connectivity

Returns connectivity details between two sites: WAN links, BGP peering, latency, reachability.

```
Parameters:
  site_a: string (required)
  site_b: string (required)

Returns: {
    site_a: string,
    site_b: string,
    wan_links: [{source, target, bandwidth, latency_ms, status}],
    bgp_sessions: [
        {
            local_device: string,
            remote_device: string,
            local_as: int,
            remote_as: int,
            state: string
        }
    ],
    reachable: bool,
    min_latency_ms: float | null
}

Errors:
  - SiteNotFound

Engine: Analysis
```

### search_devices

Unified device search with filters.

```
Parameters:
  query: string (optional) — Substring match on device ID or name
  device_type: string (optional) — Filter by type
  site: string (optional) — Filter by site
  status: "up" | "down" (optional) — Filter by status
  vendor: string (optional) — Filter by vendor

Returns: {
    results: [{id, name, device_type, site, status, vendor}],
    total: int
}

Engine: Analysis
```

At least one filter parameter is required. Returns empty list if no matches.

---

## 9. State & Comparison

### compare_with_baseline

Diffs the working twin against the baseline to show all mutations.

```
Parameters:
  (none)

Returns: {
    mutations_applied: int,
    changes: [
        {
            change_type: "device_status" | "link_status" | "link_latency" | "vlan_removed" | "vlan_added" | "bgp_peer_state" | "route_added" | "route_removed" | "prefix_withdrawn" | "prefix_advertised",
            component_id: string,
            field: string,
            baseline_value: any,
            current_value: any
        }
    ]
}

Engine: Analysis (reads both baseline and working twin)
```

---

## Tool Categories Summary

### Query Tools (21) — Available to Agent

| Category | Count | Tools |
|---|---|---|
| Device Management | 4 | get_device_info, get_device_interfaces, get_device_routes, get_device_bgp_summary |
| Link Management | 2 | get_link_info, get_links |
| VLAN Management | 2 | get_vlan_info, list_vlans |
| Routing & Path | 3 | trace_route, check_reachability, get_alternative_paths |
| Impact Analysis | 2 | get_blast_radius, get_service_dependencies |
| Redundancy | 3 | get_redundancy_status, get_single_points_of_failure, get_failover_path |
| Topology & Discovery | 4 | get_site_topology, get_site_summary, get_inter_site_connectivity, search_devices |
| State | 1 | compare_with_baseline |
| **Subtotal** | **21** | |

### Mutation Tools (13) — API Only (NOT in agent system prompt)

| Category | Count | Tools |
|---|---|---|
| Device Management | 2 | disable_device, enable_device |
| Link Management | 3 | disable_link, enable_link, set_link_latency |
| VLAN Management | 2 | add_vlan, remove_vlan |
| Routing & Path | 2 | add_static_route, remove_static_route |
| BGP | 4 | disable_bgp_peer, enable_bgp_peer, withdraw_prefix, advertise_prefix |
| **Subtotal** | **13** | |

**Grand Total: 34 unique tools** (21 query + 13 mutation)
