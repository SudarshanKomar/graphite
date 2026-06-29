"""MCP tool definitions — all 34 V1 tools + 2 meta-tools.

Each tool is a ``ToolDef`` containing enriched MCP-grade metadata and a handler
function that delegates to the analysis or simulation engine. Descriptions are
multi-sentence with parameter guidance and ID format examples, per the V2
tool-contract spec.

Categories:
  query    — read-only; available in observe and operate modes
  mutation — topology-changing; available only in operate mode
  meta     — mode/reset management; available in all modes
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class ToolDef:
    """A single MCP tool definition with dispatch handler."""

    name: str
    description: str
    input_schema: dict
    category: str  # "query" | "mutation" | "meta"
    handler: Callable[..., dict]


def _schema(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
    }


_S = {"type": "string"}
_I = {"type": "integer"}
_N = {"type": "number"}


def build_tool_defs(analysis, simulation, twin_manager, mode) -> list[ToolDef]:
    """Build all 36 tool definitions wired to the given engines.

    ``mode`` is the :class:`CapabilityMode` instance — used by the two
    meta-tools (set_capability_mode, reset_simulation).
    """
    a = analysis   # AnalysisEngine
    s = simulation  # SimulationEngine
    defs: list[ToolDef] = []

    # ===== Query tools (21) — observe + operate ========================= #

    # --- Device ---
    defs.append(ToolDef(
        "get_device_info",
        "Returns metadata and current status for a network device including "
        "type, vendor, OS, site, management IP, and operational status "
        "(up/down). Use this to inspect a specific device by its ID "
        "(e.g. 'blr-core-01').",
        _schema({"device_id": {**_S, "description": "Device ID (e.g. 'blr-core-01')"}},
                ["device_id"]),
        "query",
        lambda device_id: a.get_device_info(device_id),
    ))
    defs.append(ToolDef(
        "get_device_interfaces",
        "Returns all interfaces on a device with their IPs, status, speed, "
        "VLAN assignments, and connected peer device.",
        _schema({"device_id": {**_S, "description": "Device ID"}}, ["device_id"]),
        "query",
        lambda device_id: a.get_device_interfaces(device_id),
    ))
    defs.append(ToolDef(
        "get_device_routes",
        "Returns the routing table for a device — prefixes, next hops, "
        "protocol (static/connected/bgp), and route status.",
        _schema({"device_id": {**_S, "description": "Device ID"}}, ["device_id"]),
        "query",
        lambda device_id: a.get_device_routes(device_id),
    ))
    defs.append(ToolDef(
        "get_device_bgp_summary",
        "Returns BGP peering state for an edge router — local AS, router ID, "
        "peers with session state (established/idle), prefixes received and "
        "advertised. Returns null for non-BGP devices.",
        _schema({"device_id": {**_S, "description": "Device ID (edge router)"}},
                ["device_id"]),
        "query",
        lambda device_id: a.get_device_bgp_summary(device_id),
    ))

    # --- Link ---
    defs.append(ToolDef(
        "get_link_info",
        "Returns details for the physical link between two directly connected "
        "devices — bandwidth, latency, link type, and status.",
        _schema({
            "source": {**_S, "description": "Source device ID"},
            "target": {**_S, "description": "Target device ID"},
        }, ["source", "target"]),
        "query",
        lambda source, target: a.get_link_info(source, target),
    ))
    defs.append(ToolDef(
        "get_links",
        "List network links filtered by scope. 'site' returns intra-site "
        "links (requires 'site' param), 'wan' returns inter-site WAN/MPLS/VPN "
        "links, 'all' returns every link.",
        _schema({
            "scope": {**_S, "enum": ["site", "wan", "all"],
                      "description": "Filter scope"},
            "site": {**_S, "description": "Site short name (required when scope='site'). "
                     "Values: bangalore, london, newyork, singapore"},
        }, ["scope"]),
        "query",
        lambda scope, site=None: a.get_links(scope, site),
    ))

    # --- VLAN ---
    defs.append(ToolDef(
        "get_vlan_info",
        "Returns VLAN details including subnet, gateway, devices carrying the "
        "VLAN, associated user groups, and estimated user count. Also returns "
        "the VLAN node id (e.g. 'blr-vlan-420') needed for blast-radius.",
        _schema({
            "vlan_id": {**_I, "description": "VLAN ID (integer, e.g. 420)"},
            "site": {**_S, "description": "Site short name"},
        }, ["vlan_id", "site"]),
        "query",
        lambda vlan_id, site: a.get_vlan_info(vlan_id, site),
    ))
    defs.append(ToolDef(
        "list_vlans",
        "Returns all VLANs configured at a site with their IDs, names, "
        "subnets, and node ids.",
        _schema({"site": {**_S, "description": "Site short name"}}, ["site"]),
        "query",
        lambda site: a.list_vlans(site),
    ))

    # --- Routing & path ---
    defs.append(ToolDef(
        "trace_route",
        "Simulated hop-by-hop traceroute from source to destination following "
        "routing tables. Returns each hop with cumulative latency. Source can "
        "be a device ID, user group, or VLAN. Destination can be a device, "
        "service, or subnet.",
        _schema({
            "source": {**_S, "description": "Source (device/user_group/VLAN ID)"},
            "destination": {**_S, "description": "Destination (device/service/subnet)"},
        }, ["source", "destination"]),
        "query",
        lambda source, destination: a.trace_route(source, destination),
    ))
    defs.append(ToolDef(
        "check_reachability",
        "Boolean reachability check between source and destination. Returns "
        "whether a path exists, the path if reachable, or a failure reason.",
        _schema({
            "source": {**_S, "description": "Source ID"},
            "destination": {**_S, "description": "Destination ID"},
        }, ["source", "destination"]),
        "query",
        lambda source, destination: a.check_reachability(source, destination),
    ))
    defs.append(ToolDef(
        "get_alternative_paths",
        "Returns all available paths (including ECMP and backup) between two "
        "devices, with latency and hop count for each.",
        _schema({
            "source": {**_S, "description": "Source device ID"},
            "destination": {**_S, "description": "Destination device ID"},
        }, ["source", "destination"]),
        "query",
        lambda source, destination: a.get_alternative_paths(source, destination),
    ))

    # --- Impact ---
    defs.append(ToolDef(
        "get_blast_radius",
        "Computes the blast radius of a failed or degraded network component. "
        "Accepts a device ID (e.g. 'sg-leaf-03'), VLAN node ID "
        "(e.g. 'blr-vlan-420' — use get_vlan_info to find this), service ID "
        "(e.g. 'erp-service'), or link ID (e.g. 'link-blr-sg-wan'). Returns "
        "affected devices, services, user groups, total users impacted, "
        "severity (critical/high/medium/low), and severity factors.",
        _schema({"component_id": {**_S, "description":
                 "Component ID (device/VLAN node/service/link)"}},
                ["component_id"]),
        "query",
        lambda component_id: a.get_blast_radius(component_id),
    ))
    defs.append(ToolDef(
        "get_service_dependencies",
        "Returns the dependency graph for a service — direct and transitive "
        "dependencies, dependent services, host device, and current status.",
        _schema({"service_id": {**_S, "description": "Service ID (e.g. 'erp-service')"}},
                ["service_id"]),
        "query",
        lambda service_id: a.get_service_dependencies(service_id),
    ))

    # --- Redundancy ---
    defs.append(ToolDef(
        "get_redundancy_status",
        "Checks whether a component has redundant/backup paths or failover "
        "capability. Returns parallel link count, alternative paths, ECMP "
        "status, and risk assessment.",
        _schema({"component_id": {**_S, "description": "Device or link ID"}},
                ["component_id"]),
        "query",
        lambda component_id: a.get_redundancy_status(component_id),
    ))
    defs.append(ToolDef(
        "get_single_points_of_failure",
        "Returns all single points of failure for a site — components whose "
        "failure would isolate part of the network.",
        _schema({"site": {**_S, "description": "Site short name"}}, ["site"]),
        "query",
        lambda site: a.get_single_points_of_failure(site),
    ))
    defs.append(ToolDef(
        "get_failover_path",
        "When a primary component fails, returns the failover path (if any), "
        "its latency, and the latency increase versus the primary path.",
        _schema({"primary_component": {**_S, "description": "Device or link ID"}},
                ["primary_component"]),
        "query",
        lambda primary_component: a.get_failover_path(primary_component),
    ))

    # --- Topology & discovery ---
    defs.append(ToolDef(
        "get_site_topology",
        "Returns the full topology of a site — all devices, links, VLANs, "
        "services, and user groups.",
        _schema({"site": {**_S, "description": "Site short name"}}, ["site"]),
        "query",
        lambda site: a.get_site_topology(site),
    ))
    defs.append(ToolDef(
        "get_site_summary",
        "High-level stats and health for a site — device/link counts (up/down), "
        "VLAN count, service count, total users, and overall health status.",
        _schema({"site": {**_S, "description": "Site short name"}}, ["site"]),
        "query",
        lambda site: a.get_site_summary(site),
    ))
    defs.append(ToolDef(
        "get_inter_site_connectivity",
        "Returns WAN links and BGP peering state between two sites, including "
        "reachability and minimum latency.",
        _schema({
            "site_a": {**_S, "description": "First site short name"},
            "site_b": {**_S, "description": "Second site short name"},
        }, ["site_a", "site_b"]),
        "query",
        lambda site_a, site_b: a.get_inter_site_connectivity(site_a, site_b),
    ))
    defs.append(ToolDef(
        "search_devices",
        "Search devices by filters — substring match on name/ID, device type, "
        "site, status, or vendor. At least one filter required.",
        _schema({
            "query": {**_S, "description": "Substring match on ID or name"},
            "device_type": {**_S, "description": "Filter by type"},
            "site": {**_S, "description": "Filter by site"},
            "status": {**_S, "description": "Filter: 'up' or 'down'"},
            "vendor": {**_S, "description": "Filter by vendor"},
        }, []),
        "query",
        lambda **kw: a.search_devices(**kw),
    ))

    # --- State ---
    defs.append(ToolDef(
        "compare_with_baseline",
        "Shows all changes between the current working twin and the healthy "
        "baseline. Returns a list of mutations (device status, link status, "
        "VLAN removal, latency changes, BGP state, route changes).",
        _schema({}, []),
        "query",
        lambda: a.compare_with_baseline(),
    ))

    # ===== Mutation tools (13) — operate mode only ====================== #

    defs.append(ToolDef(
        "disable_device",
        "⚠️ MUTATION — Mark a device as down. Cascading effects: all connected "
        "links go down, hosted services go down, BGP peers drop. Requires "
        "operate mode. Changes persist until reset_simulation.",
        _schema({"device_id": {**_S, "description": "Device ID to disable"}},
                ["device_id"]),
        "mutation",
        lambda device_id: s.disable_device(device_id),
    ))
    defs.append(ToolDef(
        "enable_device",
        "⚠️ MUTATION — Restore a down device to up. Links, services, and BGP "
        "peers are restored. Requires operate mode.",
        _schema({"device_id": {**_S, "description": "Device ID to enable"}},
                ["device_id"]),
        "mutation",
        lambda device_id: s.enable_device(device_id),
    ))
    defs.append(ToolDef(
        "disable_link",
        "⚠️ MUTATION — Mark a link as down (both directions). May isolate "
        "network segments. Requires operate mode.",
        _schema({
            "source": {**_S, "description": "Source device ID"},
            "target": {**_S, "description": "Target device ID"},
        }, ["source", "target"]),
        "mutation",
        lambda source, target: s.disable_link(source, target),
    ))
    defs.append(ToolDef(
        "enable_link",
        "⚠️ MUTATION — Restore a down link (both directions). Requires "
        "operate mode.",
        _schema({
            "source": {**_S, "description": "Source device ID"},
            "target": {**_S, "description": "Target device ID"},
        }, ["source", "target"]),
        "mutation",
        lambda source, target: s.enable_link(source, target),
    ))
    defs.append(ToolDef(
        "set_link_latency",
        "⚠️ MUTATION — Change the latency of a link. Use for WAN degradation "
        "simulation. Requires operate mode.",
        _schema({
            "source": {**_S, "description": "Source device ID"},
            "target": {**_S, "description": "Target device ID"},
            "latency_ms": {**_N, "description": "New latency in milliseconds"},
        }, ["source", "target", "latency_ms"]),
        "mutation",
        lambda source, target, latency_ms: s.set_link_latency(
            source, target, latency_ms),
    ))
    defs.append(ToolDef(
        "add_vlan",
        "⚠️ MUTATION — Add or restore a VLAN to a site. Requires operate mode.",
        _schema({
            "vlan_id": {**_I, "description": "VLAN ID"},
            "site": {**_S, "description": "Site short name"},
            "subnet": {**_S, "description": "Subnet CIDR"},
            "name": {**_S, "description": "VLAN name"},
            "devices": {"type": "array", "items": _S,
                        "description": "Device IDs to carry this VLAN"},
        }, ["vlan_id", "site", "subnet", "name", "devices"]),
        "mutation",
        lambda vlan_id, site, subnet, name, devices: s.add_vlan(
            vlan_id, site, subnet, name, devices),
    ))
    defs.append(ToolDef(
        "remove_vlan",
        "⚠️ MUTATION — Remove a VLAN from a site. Disconnects user groups and "
        "unconfigures devices. Requires operate mode.",
        _schema({
            "vlan_id": {**_I, "description": "VLAN ID"},
            "site": {**_S, "description": "Site short name"},
        }, ["vlan_id", "site"]),
        "mutation",
        lambda vlan_id, site: s.remove_vlan(vlan_id, site),
    ))
    defs.append(ToolDef(
        "add_static_route",
        "⚠️ MUTATION — Add a static route to a device. Requires operate mode.",
        _schema({
            "device_id": {**_S, "description": "Device ID"},
            "prefix": {**_S, "description": "Destination prefix (CIDR)"},
            "next_hop": {**_S, "description": "Next hop device ID"},
        }, ["device_id", "prefix", "next_hop"]),
        "mutation",
        lambda device_id, prefix, next_hop: s.add_static_route(
            device_id, prefix, next_hop),
    ))
    defs.append(ToolDef(
        "remove_static_route",
        "⚠️ MUTATION — Remove a static route from a device. Requires operate mode.",
        _schema({
            "device_id": {**_S, "description": "Device ID"},
            "prefix": {**_S, "description": "Destination prefix (CIDR)"},
        }, ["device_id", "prefix"]),
        "mutation",
        lambda device_id, prefix: s.remove_static_route(device_id, prefix),
    ))
    defs.append(ToolDef(
        "disable_bgp_peer",
        "⚠️ MUTATION — Disable a BGP peer session (reciprocal). Prefixes are "
        "withdrawn, routes recalculated. Requires operate mode.",
        _schema({
            "device_id": {**_S, "description": "Device ID of BGP speaker"},
            "peer_ip": {**_S, "description": "Peer IP address"},
        }, ["device_id", "peer_ip"]),
        "mutation",
        lambda device_id, peer_ip: s.disable_bgp_peer(device_id, peer_ip),
    ))
    defs.append(ToolDef(
        "enable_bgp_peer",
        "⚠️ MUTATION — Re-enable a BGP peer session (reciprocal). Requires "
        "operate mode.",
        _schema({
            "device_id": {**_S, "description": "Device ID"},
            "peer_ip": {**_S, "description": "Peer IP address"},
        }, ["device_id", "peer_ip"]),
        "mutation",
        lambda device_id, peer_ip: s.enable_bgp_peer(device_id, peer_ip),
    ))
    defs.append(ToolDef(
        "withdraw_prefix",
        "⚠️ MUTATION — Withdraw a BGP prefix advertisement. Requires operate mode.",
        _schema({
            "device_id": {**_S, "description": "Device ID"},
            "prefix": {**_S, "description": "Prefix (CIDR)"},
        }, ["device_id", "prefix"]),
        "mutation",
        lambda device_id, prefix: s.withdraw_prefix(device_id, prefix),
    ))
    defs.append(ToolDef(
        "advertise_prefix",
        "⚠️ MUTATION — Advertise a BGP prefix. Requires operate mode.",
        _schema({
            "device_id": {**_S, "description": "Device ID"},
            "prefix": {**_S, "description": "Prefix (CIDR)"},
        }, ["device_id", "prefix"]),
        "mutation",
        lambda device_id, prefix: s.advertise_prefix(device_id, prefix),
    ))

    # ===== Meta-tools (2) — all modes =================================== #

    defs.append(ToolDef(
        "set_capability_mode",
        "Switch the agent's capability mode. 'observe' (default) allows only "
        "read-only query tools. 'operate' enables topology-changing mutation "
        "tools (destructive, restorative, and analytical). Mode change takes "
        "effect immediately.",
        _schema({"mode": {**_S, "enum": ["observe", "operate"],
                          "description": "Target mode: 'observe' or 'operate'"}},
                ["mode"]),
        "meta",
        lambda *, mode=None, _cap=mode: _cap.switch(mode),
    ))
    defs.append(ToolDef(
        "reset_simulation",
        "Reset the working twin to the healthy baseline state, discarding all "
        "active mutations. The capability mode is preserved. Returns the "
        "number of mutations cleared.",
        _schema({}, []),
        "meta",
        lambda: _do_reset(simulation, twin_manager),
    ))

    return defs


def _do_reset(simulation, twin_manager) -> dict:
    """Reset handler — clears simulation state and returns summary."""
    log = simulation.get_mutation_log()
    count = len(log)
    simulation.reset()
    return {"mutations_cleared": count, "working_twin": "reset_to_baseline"}
