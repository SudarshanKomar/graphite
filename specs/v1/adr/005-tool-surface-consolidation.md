# ADR-005: Tool Surface Consolidation

**Status**: Accepted  
**Date**: 2025-06-22  
**Deciders**: Architecture Lead  

---

## Context

The initial tool surface proposal contained ~50 tools. For an LLM-based agent, tool count directly impacts:
- **Selection accuracy**: More tools → more confusion about which to call
- **Prompt size**: Each tool's schema consumes tokens in the system prompt
- **Maintenance burden**: Each tool needs implementation, tests, error handling

## Decision

Consolidate to **34 tools** organized in 9 categories, split into 21 query tools (exposed to agent) and 13 mutation tools (API-only). Remove redundancy, merge overlapping tools, ensure every tool earns its place.

### Consolidation Principles

1. **Merge if same data, different filter**: `get_site_links` + `get_wan_links` → `get_links(scope=...)` 
2. **Merge if output is subset**: `get_affected_users` + `get_affected_services` → include in `get_blast_radius` output
3. **Remove if trivially composable**: `find_devices_by_type` is just `search_devices(type=...)` with a filter
4. **Remove duplicates**: `get_service_dependencies` appeared in both Impact Analysis and Service Analysis
5. **Keep if conceptually distinct**: `trace_route` (hop-by-hop with latency) vs `check_reachability` (boolean) serve different reasoning needs

### Final Tool Surface (34 tools)

#### Device Management (6)
| Tool | Purpose |
|---|---|
| `get_device_info` | Device metadata, status, site |
| `get_device_interfaces` | Interfaces with IPs, VLANs, status |
| `get_device_routes` | Routing table for device |
| `get_device_bgp_summary` | BGP peers, state, prefixes for device |
| `disable_device` | Mark device down + cascade effects |
| `enable_device` | Mark device up + restore effects |

#### Link Management (5)
| Tool | Purpose |
|---|---|
| `get_link_info` | Link details between two devices |
| `get_links` | List links filtered by scope (site/wan/all) |
| `disable_link` | Mark link down + cascade |
| `enable_link` | Mark link up + restore |
| `set_link_latency` | Change link latency |

#### VLAN Management (4)
| Tool | Purpose |
|---|---|
| `get_vlan_info` | VLAN details including devices, user count |
| `list_vlans` | All VLANs at a site |
| `add_vlan` | Add VLAN to site |
| `remove_vlan` | Remove VLAN from site + cascade |

#### Routing & Path (5)
| Tool | Purpose |
|---|---|
| `trace_route` | Hop-by-hop path with latency per hop |
| `check_reachability` | Boolean reachability + path if reachable |
| `get_alternative_paths` | All paths including ECMP/backup |
| `add_static_route` | Add static route to device |
| `remove_static_route` | Remove static route from device |

#### BGP (4)
| Tool | Purpose |
|---|---|
| `disable_bgp_peer` | Disable peer session + withdraw prefixes |
| `enable_bgp_peer` | Enable peer session + re-advertise |
| `withdraw_prefix` | Withdraw specific prefix |
| `advertise_prefix` | Advertise specific prefix |

Note: BGP queries use `get_device_bgp_summary` from Device Management. The previous `get_bgp_summary` alias has been removed to avoid agent confusion.

#### Impact Analysis (2)
| Tool | Purpose |
|---|---|
| `get_blast_radius` | Full impact: affected devices, services, users, severity |
| `get_service_dependencies` | Dependency graph for a service |

#### Redundancy Analysis (3)
| Tool | Purpose |
|---|---|
| `get_redundancy_status` | Check if component has redundant paths |
| `get_single_points_of_failure` | SPOFs for a site |
| `get_failover_path` | Alternative path if primary fails |

#### Topology & Discovery (4)
| Tool | Purpose |
|---|---|
| `get_site_topology` | Full topology of a site (devices, links, VLANs) |
| `get_site_summary` | High-level site stats (counts, health) |
| `get_inter_site_connectivity` | WAN links and BGP state between two sites |
| `search_devices` | Search by name, type, vendor, site (unified) |

#### State & Comparison (1)
| Tool | Purpose |
|---|---|
| `compare_with_baseline` | Diff working twin vs baseline |

**Total: 34 tools** (21 query + 13 mutation)

Plus `final_answer` (agent-internal, not a network tool).

**Important**: Only the 21 query tools appear in the agent's system prompt. Mutation tools are invoked via the `POST /simulation/inject` API endpoint, not by the agent. This prevents the agent from accidentally mutating state during investigation.

### What Was Removed/Merged

| Original Tool | Disposition |
|---|---|
| `get_device_vlans` | Merged into `get_device_interfaces` (VLANs are per-interface) |
| `get_device_bgp_peers` | Renamed to `get_device_bgp_summary` (clearer) |
| `set_link_bandwidth` | Removed — bandwidth changes rarely drive demo scenarios, can add later |
| `get_site_links` | Merged into `get_links(scope="site", site=...)` |
| `get_wan_links` | Merged into `get_links(scope="wan")` |
| `get_vlan_devices` | Merged into `get_vlan_info` (returns devices list) |
| `get_vlan_users` | Merged into `get_vlan_info` (returns user count) |
| `get_route_path` | Removed — overlaps with `trace_route` |
| `get_shortest_path` | Removed — overlaps with `trace_route` |
| `get_lowest_latency_path` | Removed — overlaps with `get_alternative_paths` (returns paths sorted by latency) |
| `get_bgp_prefixes` | Merged into `get_device_bgp_summary` |
| `get_bgp_as_path` | Removed — derivable from `trace_route` between sites |
| `get_affected_users` | Merged into `get_blast_radius` output |
| `get_affected_services` | Merged into `get_blast_radius` output |
| `check_ecmp_status` | Merged into `get_redundancy_status` |
| `get_site_devices` | Merged into `get_site_topology` |
| `get_site_vlans` | Merged into `get_site_topology` |
| `get_service_info` | Merged into `get_service_dependencies` (returns service info + deps) |
| `check_service_health` | Made a field in `get_service_dependencies` output |
| `get_current_state` | Replaced with `compare_with_baseline` (more useful) |
| `get_latency_matrix` | Removed — derivable from `trace_route` calls, rarely needed by agent |
| `find_devices_by_type` | Merged into `search_devices(type=...)` |
| `find_path_between_sites` | Merged into `get_inter_site_connectivity` |

## Consequences

**Positive:**
- 30% fewer tools → better agent tool selection accuracy
- Smaller system prompt → more room for conversation history
- Less implementation work
- Each tool has clear, non-overlapping purpose

**Negative:**
- Some tools return larger payloads (e.g., `get_blast_radius` returns devices + services + users)
- Agent may need to parse richer output structures

## Implementation Notes

- Full tool schemas in `specs/schemas/tool-schemas.md`
- Tools are registered in a `ToolRegistry` at startup
- Each tool is a Python function that takes the working twin graph and parameters, returns structured data
- Mutation tools (disable_*, remove_*, etc.) go through the simulation engine
- Query tools go through the analysis engine
