# MCP Tool Contracts

Complete tool surface exposed by the Graphite MCP Server. All 34 V1 tools are migrated plus 2 meta-tools for mode/reset management.

---

## Tool Inventory

### Meta-Tools (2) — Available in all modes

| Tool | Category | Description |
|---|---|---|
| `set_capability_mode` | meta | Switch between observe (read-only) and operate (full topology control) modes |
| `reset_simulation` | meta | Reset working twin to baseline (clear all mutations) |

### Query Tools (21) — Available in all modes

Unchanged from V1. See `specs/v1/schemas/tool-schemas.md` sections 1–4, 6–9 for full parameter/return schemas.

| Tool | Engine |
|---|---|
| `get_device_info` | Analysis |
| `get_device_interfaces` | Analysis |
| `get_device_routes` | Analysis |
| `get_device_bgp_summary` | Analysis |
| `get_link_info` | Analysis |
| `get_links` | Analysis |
| `get_vlan_info` | Analysis |
| `list_vlans` | Analysis |
| `trace_route` | Analysis |
| `check_reachability` | Analysis |
| `get_alternative_paths` | Analysis |
| `get_blast_radius` | Analysis |
| `get_service_dependencies` | Analysis |
| `get_redundancy_status` | Analysis |
| `get_single_points_of_failure` | Analysis |
| `get_failover_path` | Analysis |
| `get_site_topology` | Analysis |
| `get_site_summary` | Analysis |
| `get_inter_site_connectivity` | Analysis |
| `search_devices` | Analysis |
| `compare_with_baseline` | Analysis |

### Mutation Tools (13) — Operate mode only

| Tool | Engine |
|---|---|
| `disable_device` | Simulation |
| `enable_device` | Simulation |
| `disable_link` | Simulation |
| `enable_link` | Simulation |
| `set_link_latency` | Simulation |
| `add_vlan` | Simulation |
| `remove_vlan` | Simulation |
| `add_static_route` | Simulation |
| `remove_static_route` | Simulation |
| `disable_bgp_peer` | Simulation |
| `enable_bgp_peer` | Simulation |
| `withdraw_prefix` | Simulation |
| `advertise_prefix` | Simulation |

**Total: 36 tools** (21 query + 13 mutation + 2 meta)

---

## Meta-Tool Schemas

### set_capability_mode

```json
{
    "name": "set_capability_mode",
    "description": "Switch the agent's capability mode. 'observe' (default) allows only read-only query tools. 'operate' additionally allows topology-changing mutation tools (destructive, restorative, and analytical). Mode change takes effect immediately.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["observe", "operate"],
                "description": "Target capability mode: 'observe' for read-only, 'operate' for full topology control"
            }
        },
        "required": ["mode"]
    }
}
```

Returns:
```json
{
    "previous_mode": "observe",
    "current_mode": "operate",
    "available_tools": 36,
    "mutation_tools_enabled": true
}
```

### reset_simulation

```json
{
    "name": "reset_simulation",
    "description": "Reset the working twin to baseline state, discarding all active mutations. Mode is preserved. Returns the number of mutations that were cleared.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
```

Returns:
```json
{
    "mutations_cleared": 3,
    "working_twin": "reset_to_baseline"
}
```

---

## Description Quality Standard

Every MCP tool description must:

1. **State what the tool does** in the first sentence
2. **Specify accepted ID formats** (e.g., "device ID like 'blr-core-01'")
3. **Describe the return shape** briefly (e.g., "Returns affected devices, services, users, severity")
4. **Note mode restrictions** if mutation (e.g., "Requires operate mode")
5. **Include usage guidance** for non-obvious parameters

### Example — Full MCP Description

Tool: `get_blast_radius`

```
Computes the full blast radius of a failed or degraded network component.

Accepts a component_id which can be:
- Device ID (e.g., 'blr-core-01', 'sg-leaf-03')
- VLAN node ID (e.g., 'blr-vlan-420') — use get_vlan_info or list_vlans to find these
- Service ID (e.g., 'erp-service', 'db-cluster')
- Link ID (e.g., 'link-blr-sg-wan') — from links.json

Returns: affected devices (with impact level), affected services (with reason),
affected user groups (with user count), total users impacted, severity
(critical/high/medium/low), and the factors behind the severity rating.

Severity thresholds: critical >1000 users or critical service down;
high >100 users; medium >10 users; low <10 users.
```

---

## Tool Contract Changes from V1

| Aspect | V1 (ToolRegistry) | V2 (MCP) |
|---|---|---|
| Description length | 1-line summary | Multi-sentence with usage guidance |
| Parameter descriptions | None (bare type only) | Full description + examples |
| Mode enforcement | Registry blocks mutation tools from agent list | MCP server refuses mutation calls in observe mode |
| Return format | Python dict → JSON | MCP TextContent wrapping JSON |
| Error format | `{"error": code, "message": text}` | MCP error response OR error in TextContent (domain errors) |
| Discovery | `list_agent_tools()` method | MCP `tools/list` protocol method |

---

## Error Handling Strategy

### Protocol Errors (MCP-level)

- Unknown tool → `McpError(INVALID_PARAMS)`
- Mode violation (mutation in observe mode) → `McpError(INVALID_REQUEST)` with guidance message
- Server fault → `McpError(INTERNAL_ERROR)`

### Domain Errors (Graphite-level)

- `DeviceNotFound`, `VlanNotFound`, etc. → returned as successful tool result with error payload:

```json
{
    "error": "DeviceNotFound",
    "message": "Device 'blr-fake-01' not found"
}
```

This matches V1 behavior where domain errors are observations the agent can adapt to (not protocol failures). The agent sees the error message, adjusts its approach, and tries a different tool or parameter.
