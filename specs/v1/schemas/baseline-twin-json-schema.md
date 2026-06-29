# Baseline Twin JSON Schema

Complete schema for all JSON source-of-truth files. These files are loaded at startup to build the baseline graph.

---

## File Structure

```
network_state/
├── sites/
│   ├── bangalore.json
│   ├── london.json
│   ├── newyork.json
│   └── singapore.json
├── devices.json
├── links.json
├── vlans.json
├── bgp_peers.json
├── services.json
├── user_groups.json
└── telemetry_snapshot.json
```

**Change from handoff**: `routes.json` is removed as a top-level file. Routes are embedded in `devices.json` per device (they're device-local state, not global). Added `bgp_peers.json` (was previously undefined), `user_groups.json` (was missing), and renamed `telemetry.json` → `telemetry_snapshot.json` (clarity).

---

## sites/{site_name}.json

Site metadata. One file per site.

```json
{
    "id": "site-bangalore",
    "name": "Bangalore Campus",
    "short_name": "bangalore",
    "location": {
        "city": "Bangalore",
        "country": "India",
        "timezone": "Asia/Kolkata"
    },
    "as_number": 65001,
    "prefix_block": "10.10.0.0/14",
    "employee_count": 8000,
    "description": "Primary engineering campus and HQ"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique ID, format: `site-{short_name}` |
| `name` | string | yes | Human-readable name |
| `short_name` | string | yes | Short identifier (used in device IDs) |
| `location.city` | string | yes | City name |
| `location.country` | string | yes | Country name |
| `location.timezone` | string | no | IANA timezone |
| `as_number` | integer | yes | BGP Autonomous System number |
| `prefix_block` | string | yes | Aggregate IP prefix for this site (CIDR) |
| `employee_count` | integer | yes | Approximate employee count |
| `description` | string | no | Human description of site role |

---

## devices.json

Flat array of all devices across all sites.

```json
[
    {
        "id": "blr-core-01",
        "name": "BLR Core Switch 1",
        "type": "core_switch",
        "vendor": "Dell",
        "model": "PowerSwitch Z9664F-ON",
        "os": "SONiC",
        "site": "bangalore",
        "status": "up",
        "management_ip": "10.10.254.1",
        "role": "Campus backbone, inter-VLAN routing",
        "interfaces": [
            {
                "name": "Ethernet1/1",
                "ip_address": "10.10.1.1/30",
                "status": "up",
                "speed": "100G",
                "connected_to": "blr-edge-01",
                "vlan_mode": "trunk",
                "allowed_vlans": [110, 120, 130, 420, 500, 600, 700]
            },
            {
                "name": "Ethernet1/2",
                "ip_address": "10.10.1.5/30",
                "status": "up",
                "speed": "40G",
                "connected_to": "blr-dist-01",
                "vlan_mode": "trunk",
                "allowed_vlans": [110, 120, 420]
            }
        ],
        "routes": [
            {
                "prefix": "0.0.0.0/0",
                "next_hop": "blr-edge-01",
                "next_hop_ip": "10.10.1.2",
                "protocol": "static",
                "metric": 1,
                "status": "active"
            },
            {
                "prefix": "10.42.0.0/16",
                "next_hop": "local",
                "next_hop_ip": null,
                "protocol": "connected",
                "metric": 0,
                "status": "active"
            }
        ]
    }
]
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique device ID. Format: `{site_prefix}-{role}-{number}` |
| `name` | string | yes | Human-readable name |
| `type` | enum | yes | One of: `router`, `core_switch`, `access_switch`, `distribution_switch`, `leaf_switch`, `spine_switch`, `firewall`, `load_balancer`, `server`, `access_point` |
| `vendor` | string | yes | Vendor name (e.g., "Dell", "Cisco") |
| `model` | string | no | Model number |
| `os` | string | yes | Operating system (e.g., "SONiC", "OS10", "IOS-XE") |
| `site` | string | yes | Site short_name this device belongs to |
| `status` | enum | yes | `up` or `down` |
| `management_ip` | string | no | Management IP address |
| `role` | string | no | Free-text description of device role |
| `interfaces` | array | yes | List of interface objects (see below) |
| `routes` | array | yes | List of route entries (see below). Empty `[]` for non-routing devices |

### Interface Object

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Interface name (e.g., "Ethernet1/1") |
| `ip_address` | string | no | IP with CIDR (null for L2-only ports) |
| `status` | enum | yes | `up` or `down` |
| `speed` | string | no | Port speed (e.g., "100G", "10G", "1G") |
| `connected_to` | string | no | Device ID this interface connects to (null if unconnected) |
| `vlan_mode` | enum | no | `access` or `trunk` (null for L3 ports) |
| `allowed_vlans` | array[int] | no | VLAN IDs allowed (trunk mode) |
| `access_vlan` | integer | no | VLAN ID assigned (access mode) |

### Route Entry Object

| Field | Type | Required | Description |
|---|---|---|---|
| `prefix` | string | yes | Destination prefix in CIDR |
| `next_hop` | string | yes | Next hop device ID, or `"local"` for connected routes |
| `next_hop_ip` | string | no | Next hop IP address |
| `protocol` | enum | yes | `static`, `connected`, `bgp`, `ospf` |
| `metric` | integer | no | Route metric / preference |
| `status` | enum | yes | `active` or `inactive` |

---

## links.json

All physical links (inter-device connections). Each link appears ONCE (not duplicated for both directions — the builder creates bidirectional graph edges).

```json
[
    {
        "id": "link-blr-core01-edge01",
        "source": "blr-core-01",
        "target": "blr-edge-01",
        "source_interface": "Ethernet1/1",
        "target_interface": "Ethernet1/1",
        "bandwidth": "100G",
        "latency_ms": 0.5,
        "link_type": "campus",
        "status": "up"
    },
    {
        "id": "link-blr-sg-wan",
        "source": "blr-edge-01",
        "target": "sg-edge-01",
        "source_interface": "Ethernet2/1",
        "target_interface": "Ethernet2/1",
        "bandwidth": "10G",
        "latency_ms": 55,
        "link_type": "wan",
        "status": "up"
    }
]
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique link identifier |
| `source` | string | yes | Source device ID |
| `target` | string | yes | Target device ID |
| `source_interface` | string | no | Interface name on source device |
| `target_interface` | string | no | Interface name on target device |
| `bandwidth` | string | yes | Link bandwidth (e.g., "100G", "10G", "1G") |
| `latency_ms` | number | yes | One-way latency in milliseconds |
| `link_type` | enum | yes | `campus`, `datacenter`, `wan`, `mpls`, `vpn` |
| `status` | enum | yes | `up` or `down` |

---

## vlans.json

All VLANs across all sites.

```json
[
    {
        "vlan_id": 420,
        "name": "Corp WiFi",
        "subnet": "10.42.0.0/16",
        "gateway": "10.42.0.1",
        "site": "bangalore",
        "description": "Corporate wireless network for employees",
        "devices": ["blr-core-01", "blr-core-02", "blr-dist-01", "blr-dist-02", "blr-access-f1", "blr-access-f2"]
    },
    {
        "vlan_id": 110,
        "name": "Engineering LAN",
        "subnet": "10.11.0.0/16",
        "gateway": "10.11.0.1",
        "site": "bangalore",
        "description": "Wired engineering workstations",
        "devices": ["blr-core-01", "blr-core-02", "blr-dist-01", "blr-access-f1"]
    }
]
```

| Field | Type | Required | Description |
|---|---|---|---|
| `vlan_id` | integer | yes | VLAN ID (1-4094) |
| `name` | string | yes | Human-readable VLAN name |
| `subnet` | string | yes | IP subnet in CIDR |
| `gateway` | string | yes | Default gateway IP |
| `site` | string | yes | Site short_name |
| `description` | string | no | Description of VLAN purpose |
| `devices` | array[string] | yes | List of device IDs that carry this VLAN |

**Uniqueness**: The combination of `(vlan_id, site)` must be unique. Same VLAN ID can exist at multiple sites.

---

## bgp_peers.json

BGP peering sessions. Each entry represents one peering relationship on one device.

```json
[
    {
        "device": "blr-edge-01",
        "local_as": 65001,
        "router_id": "10.10.0.1",
        "peers": [
            {
                "peer_ip": "10.99.12.2",
                "peer_device": "lon-edge-01",
                "peer_as": 65002,
                "state": "established",
                "prefixes_received": ["10.20.0.0/16"],
                "prefixes_advertised": ["10.10.0.0/14"]
            },
            {
                "peer_ip": "10.99.14.2",
                "peer_device": "sg-edge-01",
                "peer_as": 65004,
                "state": "established",
                "prefixes_received": ["10.50.0.0/14"],
                "prefixes_advertised": ["10.10.0.0/14"]
            }
        ]
    }
]
```

| Field | Type | Required | Description |
|---|---|---|---|
| `device` | string | yes | Device ID of the BGP speaker |
| `local_as` | integer | yes | Local AS number |
| `router_id` | string | yes | BGP router ID (typically a loopback IP) |
| `peers` | array | yes | List of peer objects |
| `peers[].peer_ip` | string | yes | Peer's IP address |
| `peers[].peer_device` | string | yes | Peer's device ID |
| `peers[].peer_as` | integer | yes | Peer's AS number |
| `peers[].state` | enum | yes | `established`, `idle`, `active` |
| `peers[].prefixes_received` | array[string] | yes | Prefixes learned from peer (CIDR) |
| `peers[].prefixes_advertised` | array[string] | yes | Prefixes advertised to peer (CIDR) |

---

## services.json

Application services hosted in the network.

```json
[
    {
        "id": "erp-service",
        "name": "Enterprise Resource Planning",
        "type": "web_application",
        "site": "singapore",
        "host_device": "sg-server-01",
        "port": 443,
        "protocol": "https",
        "status": "healthy",
        "criticality": "critical",
        "depends_on": ["auth-service", "db-cluster"],
        "description": "Core ERP system used by all offices"
    },
    {
        "id": "auth-service",
        "name": "Authentication Service",
        "type": "auth",
        "site": "singapore",
        "host_device": "sg-server-02",
        "port": 8443,
        "protocol": "https",
        "status": "healthy",
        "criticality": "critical",
        "depends_on": ["db-cluster"],
        "description": "LDAP/SSO authentication for all services"
    }
]
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique service identifier |
| `name` | string | yes | Human-readable name |
| `type` | string | yes | Service type (e.g., `web_application`, `auth`, `database`, `monitoring`) |
| `site` | string | yes | Site where service is hosted |
| `host_device` | string | yes | Device ID hosting this service |
| `port` | integer | no | Service port |
| `protocol` | string | no | Protocol (e.g., `https`, `tcp`, `grpc`) |
| `status` | enum | yes | `healthy`, `degraded`, `down` |
| `criticality` | enum | yes | `critical`, `high`, `medium`, `low` |
| `depends_on` | array[string] | yes | Service IDs this service depends on. Empty `[]` if no dependencies |
| `description` | string | no | Description |

---

## user_groups.json

Aggregate user populations. NOT individual users — these represent groups of users on specific network segments.

```json
[
    {
        "id": "blr-corp-wifi-users",
        "name": "Bangalore Corporate WiFi Users",
        "site": "bangalore",
        "vlan_id": 420,
        "estimated_users": 5000,
        "device_types": ["laptop", "mobile"],
        "description": "Employees connected via corporate wireless"
    },
    {
        "id": "blr-engineering-users",
        "name": "Bangalore Engineering LAN Users",
        "site": "bangalore",
        "vlan_id": 110,
        "estimated_users": 3000,
        "device_types": ["desktop", "laptop"],
        "description": "Wired engineering workstations"
    }
]
```

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique user group ID |
| `name` | string | yes | Human-readable name |
| `site` | string | yes | Site short_name |
| `vlan_id` | integer | yes | VLAN this group connects through |
| `estimated_users` | integer | yes | Approximate user count |
| `device_types` | array[string] | no | Types of endpoints (laptop, mobile, desktop, phone, printer) |
| `description` | string | no | Description |

---

## telemetry_snapshot.json

Static telemetry data for realism. Loaded once, not updated in real-time.

```json
{
    "timestamp": "2025-06-22T10:00:00Z",
    "devices": {
        "blr-core-01": {
            "cpu_percent": 42,
            "memory_percent": 65,
            "uptime_seconds": 8640000,
            "interface_stats": {
                "Ethernet1/1": {
                    "tx_bps": 4500000000,
                    "rx_bps": 3200000000,
                    "errors_in": 0,
                    "errors_out": 0,
                    "drops_in": 12,
                    "drops_out": 0
                }
            }
        }
    }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `timestamp` | string (ISO 8601) | yes | Snapshot timestamp |
| `devices` | object | yes | Keyed by device ID |
| `devices.{id}.cpu_percent` | number | yes | CPU utilization 0-100 |
| `devices.{id}.memory_percent` | number | yes | Memory utilization 0-100 |
| `devices.{id}.uptime_seconds` | integer | no | Device uptime |
| `devices.{id}.interface_stats` | object | no | Per-interface counters |
| `devices.{id}.interface_stats.{iface}.tx_bps` | number | no | Transmit bits per second |
| `devices.{id}.interface_stats.{iface}.rx_bps` | number | no | Receive bits per second |
| `devices.{id}.interface_stats.{iface}.errors_in` | number | no | Input errors |
| `devices.{id}.interface_stats.{iface}.errors_out` | number | no | Output errors |
| `devices.{id}.interface_stats.{iface}.drops_in` | number | no | Input drops |
| `devices.{id}.interface_stats.{iface}.drops_out` | number | no | Output drops |

---

## Validation Rules

1. All device IDs referenced in links, VLANs, services, BGP peers must exist in `devices.json`
2. All site short_names must match a file in `sites/`
3. VLAN `(vlan_id, site)` pairs must be unique
4. Service dependency cycles are allowed (circular deps exist in practice) but should emit a warning
5. Link source/target devices must exist
6. BGP peer_device must exist and must also have a reciprocal peering entry
7. User group vlan_id must match a VLAN at the same site
8. All IDs (`device.id`, `link.id`, `service.id`, `user_group.id`, `site.id`) must be globally unique — no duplicate IDs across or within files
9. Interface `connected_to` references must point to valid device IDs

## Builder Defaults (Not in JSON)

The TwinBuilder sets these attributes during graph construction — they are NOT stored in JSON files:

- **VLAN `status`**: Set to `"active"` for all VLANs loaded from JSON
- **Device `bgp_state`**: Merged from `bgp_peers.json` into the matching device node
- **Device `telemetry`**: Merged from `telemetry_snapshot.json` into the matching device node
- **Field renames**: `device.type` → `device_type`, `service.type` → `service_type` (avoid Python builtin collision)
