"""Topology, inventory, and discovery queries.

Houses the straightforward read tools (device/link/VLAN inventory, site
topology and summary, inter-site connectivity, device search) plus the site
health calculation from ``specs/schemas/tool-schemas.md``.
"""

from __future__ import annotations

from typing import Optional

from ..errors import (
    DeviceNotFound,
    LinkNotFound,
    SiteNotFound,
    VlanNotFound,
)
from ..twin.graph_wrapper import GraphWrapper

_WAN_LINK_TYPES = {"wan", "mpls", "vpn"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_device(graph: GraphWrapper, device_id: str) -> dict:
    if not graph.node_exists(device_id) or graph.get_node_type(device_id) != "device":
        raise DeviceNotFound(f"Device '{device_id}' not found")
    return graph.get_node(device_id)


def _require_site(graph: GraphWrapper, site: str) -> None:
    if not graph.node_exists(f"site-{site}"):
        raise SiteNotFound(f"Site '{site}' not found")


def _vlan_node(graph: GraphWrapper, vlan_id: int, site: str) -> dict:
    for vlan in graph.get_vlans(site=site):
        if vlan.get("vlan_id") == vlan_id:
            return vlan
    raise VlanNotFound(f"VLAN {vlan_id} not found at site '{site}'")


def _dedup_links(edges) -> list[dict]:
    """Collapse bidirectional physical_link pairs to one entry per link_id."""
    seen: set[str] = set()
    out = []
    for src, dst, data in edges:
        link_id = data.get("link_id")
        if link_id in seen:
            continue
        seen.add(link_id)
        out.append({
            "link_id": link_id,
            "source": src,
            "target": dst,
            "bandwidth": data.get("bandwidth"),
            "latency_ms": data.get("latency_ms"),
            "link_type": data.get("link_type"),
            "status": data.get("status"),
        })
    return out


# ---------------------------------------------------------------------------
# Device inventory
# ---------------------------------------------------------------------------
def get_device_info(graph: GraphWrapper, device_id: str) -> dict:
    node = _require_device(graph, device_id)
    return {
        "id": device_id,
        "name": node.get("name"),
        "device_type": node.get("device_type"),
        "vendor": node.get("vendor"),
        "model": node.get("model"),
        "os": node.get("os"),
        "site": node.get("site"),
        "status": node.get("status"),
        "management_ip": node.get("management_ip"),
        "role": node.get("role"),
    }


def get_device_interfaces(graph: GraphWrapper, device_id: str) -> dict:
    node = _require_device(graph, device_id)
    return {"device_id": device_id, "interfaces": node.get("interfaces", [])}


def get_device_routes(graph: GraphWrapper, device_id: str) -> dict:
    node = _require_device(graph, device_id)
    return {"device_id": device_id, "routes": node.get("routes", [])}


def get_device_bgp_summary(graph: GraphWrapper, device_id: str) -> Optional[dict]:
    node = _require_device(graph, device_id)
    bgp = node.get("bgp_state")
    if not bgp:
        return None
    return {
        "device_id": device_id,
        "local_as": bgp.get("local_as"),
        "router_id": bgp.get("router_id"),
        "peers": bgp.get("peers", []),
    }


# ---------------------------------------------------------------------------
# Link inventory
# ---------------------------------------------------------------------------
def get_link_info(graph: GraphWrapper, source: str, target: str) -> dict:
    edge = graph.find_link_edge(source, target)
    if edge is None:
        raise LinkNotFound(f"No link between '{source}' and '{target}'")
    return {
        "link_id": edge.get("link_id"),
        "source": source,
        "target": target,
        "bandwidth": edge.get("bandwidth"),
        "latency_ms": edge.get("latency_ms"),
        "link_type": edge.get("link_type"),
        "status": edge.get("status"),
    }


def get_links(graph: GraphWrapper, scope: str, site: Optional[str] = None) -> dict:
    all_edges = graph.get_edges_by_relation("physical_link")
    if scope == "site":
        if not site:
            raise SiteNotFound("Parameter 'site' required when scope='site'")
        _require_site(graph, site)
        site_devices = {d["id"] for d in graph.get_devices(site=site)}
        edges = [(s, d, data) for s, d, data in all_edges
                 if s in site_devices and d in site_devices]
    elif scope == "wan":
        edges = [(s, d, data) for s, d, data in all_edges
                 if data.get("link_type") in _WAN_LINK_TYPES]
    elif scope == "all":
        edges = all_edges
    else:
        raise ValueError(f"Invalid scope '{scope}' (expected site|wan|all)")

    return {"scope": scope, "site": site, "links": _dedup_links(edges)}


# ---------------------------------------------------------------------------
# VLAN inventory
# ---------------------------------------------------------------------------
def get_vlan_info(graph: GraphWrapper, vlan_id: int, site: str) -> dict:
    _require_site(graph, site)
    vlan = _vlan_node(graph, vlan_id, site)
    vlan_node_id = vlan["id"]
    devices = graph.get_vlan_devices(vlan_node_id)

    user_groups = []
    total_users = 0
    for grp in graph.get_user_groups(site=site):
        if grp.get("vlan_id") == vlan_id:
            user_groups.append({
                "id": grp["id"],
                "name": grp.get("name"),
                "estimated_users": grp.get("estimated_users", 0),
            })
            total_users += grp.get("estimated_users", 0)

    return {
        "id": vlan_node_id,
        "vlan_id": vlan_id,
        "name": vlan.get("name"),
        "subnet": vlan.get("subnet"),
        "gateway": vlan.get("gateway"),
        "site": site,
        "status": vlan.get("status"),
        "devices": sorted(devices),
        "user_groups": user_groups,
        "total_estimated_users": total_users,
    }


def list_vlans(graph: GraphWrapper, site: str) -> dict:
    _require_site(graph, site)
    vlans = [{
        "id": v.get("id"),
        "vlan_id": v.get("vlan_id"),
        "name": v.get("name"),
        "subnet": v.get("subnet"),
        "status": v.get("status"),
    } for v in sorted(graph.get_vlans(site=site), key=lambda x: x.get("vlan_id", 0))]
    return {"site": site, "vlans": vlans}


# ---------------------------------------------------------------------------
# Site topology & summary
# ---------------------------------------------------------------------------
def get_site_topology(graph: GraphWrapper, site: str) -> dict:
    _require_site(graph, site)
    site_node = graph.get_node(f"site-{site}")
    devices = [{
        "id": d["id"], "name": d.get("name"),
        "device_type": d.get("device_type"), "status": d.get("status"),
    } for d in graph.get_devices(site=site)]

    links = get_links(graph, scope="site", site=site)["links"]
    links = [{
        "source": l["source"], "target": l["target"],
        "bandwidth": l["bandwidth"], "latency_ms": l["latency_ms"],
        "status": l["status"],
    } for l in links]

    vlans = [{
        "id": v.get("id"),
        "vlan_id": v.get("vlan_id"), "name": v.get("name"),
        "subnet": v.get("subnet"), "status": v.get("status"),
    } for v in graph.get_vlans(site=site)]

    services = [{
        "id": s["id"], "name": s.get("name"),
        "status": s.get("status"), "criticality": s.get("criticality"),
    } for s in graph.get_services(site=site)]

    user_groups = [{
        "id": g["id"], "name": g.get("name"),
        "estimated_users": g.get("estimated_users", 0),
    } for g in graph.get_user_groups(site=site)]

    return {
        "site": site,
        "site_name": site_node.get("name"),
        "devices": devices,
        "links": links,
        "vlans": vlans,
        "services": services,
        "user_groups": user_groups,
    }


def get_site_summary(graph: GraphWrapper, site: str) -> dict:
    _require_site(graph, site)
    devices = graph.get_devices(site=site)
    device_count = len(devices)
    devices_up = sum(1 for d in devices if d.get("status") == "up")
    devices_down = device_count - devices_up

    links = get_links(graph, scope="site", site=site)["links"]
    links_up = sum(1 for l in links if l.get("status") == "up")
    links_down = len(links) - links_up

    user_groups = graph.get_user_groups(site=site)
    total_users = sum(g.get("estimated_users", 0) for g in user_groups)

    health = _site_health(devices, links_down)

    return {
        "site": site,
        "device_count": device_count,
        "devices_up": devices_up,
        "devices_down": devices_down,
        "link_count": len(links),
        "links_up": links_up,
        "links_down": links_down,
        "vlan_count": len(graph.get_vlans(site=site)),
        "service_count": len(graph.get_services(site=site)),
        "total_users": total_users,
        "health": health,
    }


def _site_health(devices: list[dict], links_down: int) -> str:
    device_count = len(devices) or 1
    down = [d for d in devices if d.get("status") == "down"]
    critical_types = {"router", "core_switch"}
    critical_down = any(d.get("device_type") in critical_types for d in down)

    if critical_down or len(down) > device_count * 0.5:
        return "critical"
    if down or links_down > 0:
        return "degraded"
    return "healthy"


# ---------------------------------------------------------------------------
# Inter-site connectivity
# ---------------------------------------------------------------------------
def get_inter_site_connectivity(graph: GraphWrapper, site_a: str, site_b: str) -> dict:
    _require_site(graph, site_a)
    _require_site(graph, site_b)

    devices_a = {d["id"] for d in graph.get_devices(site=site_a)}
    devices_b = {d["id"] for d in graph.get_devices(site=site_b)}

    wan_links = []
    for src, dst, data in graph.get_edges_by_relation("physical_link"):
        if data.get("link_type") not in _WAN_LINK_TYPES:
            continue
        if (src in devices_a and dst in devices_b):
            wan_links.append({
                "source": src, "target": dst,
                "bandwidth": data.get("bandwidth"),
                "latency_ms": data.get("latency_ms"),
                "status": data.get("status"),
            })

    bgp_sessions = []
    for dev_id in devices_a:
        node = graph.get_node(dev_id)
        bgp = node.get("bgp_state")
        if not bgp:
            continue
        for peer in bgp.get("peers", []):
            if peer.get("peer_device") in devices_b:
                bgp_sessions.append({
                    "local_device": dev_id,
                    "remote_device": peer.get("peer_device"),
                    "local_as": bgp.get("local_as"),
                    "remote_as": peer.get("peer_as"),
                    "state": peer.get("state"),
                })

    up_links = [w for w in wan_links if w["status"] == "up"]
    reachable = len(up_links) > 0
    min_latency = min((w["latency_ms"] for w in up_links), default=None)

    return {
        "site_a": site_a,
        "site_b": site_b,
        "wan_links": wan_links,
        "bgp_sessions": bgp_sessions,
        "reachable": reachable,
        "min_latency_ms": min_latency,
    }


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
def search_devices(graph: GraphWrapper, query: Optional[str] = None,
                   device_type: Optional[str] = None, site: Optional[str] = None,
                   status: Optional[str] = None, vendor: Optional[str] = None) -> dict:
    if not any([query, device_type, site, status, vendor]):
        return {"results": [], "total": 0}

    results = []
    for dev in graph.get_devices(site=site, device_type=device_type, status=status):
        if vendor and dev.get("vendor") != vendor:
            continue
        if query:
            q = query.lower()
            if q not in dev["id"].lower() and q not in (dev.get("name", "").lower()):
                continue
        results.append({
            "id": dev["id"],
            "name": dev.get("name"),
            "device_type": dev.get("device_type"),
            "site": dev.get("site"),
            "status": dev.get("status"),
            "vendor": dev.get("vendor"),
        })
    results.sort(key=lambda d: d["id"])
    return {"results": results, "total": len(results)}
