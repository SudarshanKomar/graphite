"""Path analysis: trace_route, reachability, and alternative paths.

Routing is simulated by following device routing tables hop-by-hop with
longest-prefix match (spec-refinements Issue 5). Source/destination resolution
rules map user groups, VLANs, services, and subnets onto device IDs.
"""

from __future__ import annotations

import ipaddress
from typing import Optional

from ..errors import NodeNotFound
from ..twin.graph_wrapper import GraphWrapper

# Protocol preference for tie-breaking equal-length prefix matches.
_PROTOCOL_RANK = {"connected": 0, "static": 1, "ospf": 2, "bgp": 3}

# Device layer ordering (lower = closer to the access edge) for deterministic
# source resolution.
_ACCESS_LAYER_ORDER = {
    "access_point": 0,
    "access_switch": 1,
    "distribution_switch": 2,
    "core_switch": 3,
    "leaf_switch": 1,
    "spine_switch": 3,
    "router": 4,
    "firewall": 4,
    "server": 0,
    "load_balancer": 2,
}


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------
def _primary_ip(graph: GraphWrapper, device_id: str) -> Optional[str]:
    node = graph.get_node(device_id)
    for iface in node.get("interfaces", []):
        ip = iface.get("ip_address")
        if ip:
            return ip.split("/")[0]
    mgmt = node.get("management_ip")
    return mgmt


def _vlan_node_for_user_group(graph: GraphWrapper, group_id: str) -> Optional[str]:
    vlans = graph.get_neighbors(group_id, relation="serves", direction="in")
    return vlans[0] if vlans else None


def _resolve_vlan_to_device(graph: GraphWrapper, vlan_node_id: str,
                            prefer_access: bool = False) -> Optional[str]:
    """Resolve a VLAN node to a representative *up* carrying device.

    prefer_access=True picks the lowest-layer (access) device; otherwise the
    highest-layer (gateway/core) device, matching trace_route source vs VLAN
    gateway resolution.
    """
    devices = [d for d in graph.get_vlan_devices(vlan_node_id)
               if graph.get_node(d).get("status") == "up"]
    if not devices:
        return None

    def sort_key(dev_id: str):
        dtype = graph.get_node(dev_id).get("device_type", "")
        layer = _ACCESS_LAYER_ORDER.get(dtype, 5)
        return (layer if prefer_access else -layer, dev_id)

    return sorted(devices, key=sort_key)[0]


def resolve_source(graph: GraphWrapper, source: str) -> tuple[Optional[str], Optional[str]]:
    """Resolve a source identifier to (device_id, failure_reason)."""
    if not graph.node_exists(source):
        # Could be a subnet or unknown; sources are expected to be nodes.
        return None, f"Source '{source}' not found"
    ntype = graph.get_node_type(source)
    if ntype == "device":
        return source, None
    if ntype == "user_group":
        vlan_node = _vlan_node_for_user_group(graph, source)
        if not vlan_node:
            return None, f"User group '{source}' has no serving VLAN (disconnected)"
        dev = _resolve_vlan_to_device(graph, vlan_node, prefer_access=True)
        if not dev:
            return None, f"No active device carries VLAN for user group '{source}'"
        return dev, None
    if ntype == "vlan":
        dev = _resolve_vlan_to_device(graph, source, prefer_access=True)
        if not dev:
            return None, f"VLAN '{source}' has no active carrying device"
        return dev, None
    return None, f"Source type '{ntype}' cannot be resolved to a device"


def resolve_destination(
    graph: GraphWrapper, destination: str
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Resolve a destination to (device_id, dst_ip, failure_reason)."""
    # Subnet / CIDR destination.
    if "/" in destination and graph.node_exists(destination) is False:
        try:
            net = ipaddress.ip_network(destination, strict=False)
        except ValueError:
            return None, None, f"Destination '{destination}' is not a valid node or subnet"
        dev = _device_owning_prefix(graph, str(net))
        host_ip = str(next(net.hosts(), net.network_address))
        if not dev:
            return None, host_ip, f"No device owns subnet '{destination}'"
        return dev, host_ip, None

    if not graph.node_exists(destination):
        return None, None, f"Destination '{destination}' not found"

    ntype = graph.get_node_type(destination)
    if ntype == "device":
        return destination, _primary_ip(graph, destination), None
    if ntype == "service":
        host = graph.get_service_host(destination)
        if not host:
            return None, None, f"Service '{destination}' has no host device"
        return host, _primary_ip(graph, host), None
    if ntype == "vlan":
        dev = _resolve_vlan_to_device(graph, destination, prefer_access=False)
        gw = graph.get_node(destination).get("gateway")
        if not dev:
            return None, gw, f"VLAN '{destination}' has no active carrying device"
        return dev, gw, None
    if ntype == "user_group":
        vlan_node = _vlan_node_for_user_group(graph, destination)
        if not vlan_node:
            return None, None, f"User group '{destination}' is disconnected"
        dev = _resolve_vlan_to_device(graph, vlan_node, prefer_access=True)
        gw = graph.get_node(vlan_node).get("gateway")
        return dev, gw, None
    return None, None, f"Destination type '{ntype}' cannot be resolved"


def _device_owning_prefix(graph: GraphWrapper, prefix: str) -> Optional[str]:
    target = ipaddress.ip_network(prefix, strict=False)
    for dev in graph.get_devices():
        for route in dev.get("routes", []):
            if route.get("protocol") == "connected" and route.get("status") == "active":
                try:
                    if ipaddress.ip_network(route["prefix"], strict=False) == target:
                        return dev["id"]
                except ValueError:
                    continue
    return None


def _longest_prefix_match(routes: list[dict], dst_ip: str) -> Optional[dict]:
    addr = ipaddress.ip_address(dst_ip)
    candidates = []
    for route in routes:
        if route.get("status") != "active":
            continue
        try:
            net = ipaddress.ip_network(route["prefix"], strict=False)
        except (ValueError, KeyError):
            continue
        if addr in net:
            candidates.append((net.prefixlen, route))
    if not candidates:
        return None
    candidates.sort(
        key=lambda pr: (
            -pr[0],
            _PROTOCOL_RANK.get(pr[1].get("protocol"), 9),
            pr[1].get("metric", 9999),
        )
    )
    return candidates[0][1]


# ---------------------------------------------------------------------------
# trace_route
# ---------------------------------------------------------------------------
def trace_route(graph: GraphWrapper, source: str, destination: str) -> dict:
    src_dev, src_err = resolve_source(graph, source)
    dst_dev, dst_ip, dst_err = resolve_destination(graph, destination)

    base = {
        "source": source,
        "destination": destination,
        "reachable": False,
        "hops": [],
        "total_latency_ms": 0.0,
        "total_hops": 0,
        "failure_point": None,
    }
    if src_err or src_dev is None:
        base["failure_reason"] = src_err
        return base
    if dst_err or dst_dev is None:
        base["failure_reason"] = dst_err
        base["failure_point"] = src_dev
        return base

    hops = [_hop(graph, src_dev, 1, 0.0)]
    if src_dev == dst_dev:
        base.update(reachable=True, hops=hops, total_hops=1, total_latency_ms=0.0)
        return base

    current = src_dev
    visited = {current}
    cumulative = 0.0

    while current != dst_dev:
        node = graph.get_node(current)
        if node.get("status") == "down":
            base["failure_point"] = current
            base["failure_reason"] = f"Device '{current}' is down"
            base["hops"] = hops
            return base

        route = _longest_prefix_match(node.get("routes", []), dst_ip)
        if route is None:
            base["failure_point"] = current
            base["failure_reason"] = f"No route to {dst_ip} on '{current}'"
            base["hops"] = hops
            return base

        next_hop = route["next_hop"]
        if next_hop in ("local", None) or route.get("protocol") == "connected":
            # Destination prefix is directly connected here; step to dst if it
            # is a physical neighbour.
            if dst_dev in graph.get_physical_neighbors(current, only_up=True):
                next_hop = dst_dev
            else:
                base["failure_point"] = current
                base["failure_reason"] = (
                    f"Destination '{dst_dev}' not directly reachable from '{current}'"
                )
                base["hops"] = hops
                return base

        link = graph.find_link_edge(current, next_hop)
        if link is None or link.get("status") != "up":
            base["failure_point"] = current
            base["failure_reason"] = f"Link '{current}' -> '{next_hop}' is down or missing"
            base["hops"] = hops
            return base

        cumulative += float(link.get("latency_ms", 0.0))
        current = next_hop
        if current in visited:
            base["failure_point"] = current
            base["failure_reason"] = f"Routing loop detected at '{current}'"
            base["hops"] = hops
            return base
        visited.add(current)
        hops.append(_hop(graph, current, len(hops) + 1, round(cumulative, 3)))

    base.update(
        reachable=True,
        hops=hops,
        total_hops=len(hops),
        total_latency_ms=round(cumulative, 3),
    )
    return base


def _hop(graph: GraphWrapper, device_id: str, number: int, latency: float) -> dict:
    return {
        "hop_number": number,
        "device_id": device_id,
        "device_name": graph.get_node(device_id).get("name"),
        "latency_ms": latency,
    }


# ---------------------------------------------------------------------------
# check_reachability
# ---------------------------------------------------------------------------
def check_reachability(graph: GraphWrapper, source: str, destination: str) -> dict:
    trace = trace_route(graph, source, destination)
    return {
        "source": source,
        "destination": destination,
        "reachable": trace["reachable"],
        "path": [h["device_id"] for h in trace["hops"]] if trace["reachable"] else None,
        "failure_reason": None if trace["reachable"] else trace.get("failure_reason"),
    }


# ---------------------------------------------------------------------------
# Alternative paths
# ---------------------------------------------------------------------------
def _up_adjacency(graph: GraphWrapper) -> dict[str, list[tuple[str, float]]]:
    adj: dict[str, list[tuple[str, float]]] = {}
    for src, dst, data in graph.get_edges_by_relation("physical_link"):
        if data.get("status") != "up":
            continue
        if graph.get_node(src).get("status") == "down":
            continue
        if graph.get_node(dst).get("status") == "down":
            continue
        adj.setdefault(src, []).append((dst, float(data.get("latency_ms", 0.0))))
    return adj


def _enumerate_paths(adj: dict[str, list[tuple[str, float]]], src: str, dst: str,
                     cutoff: int = 9, max_paths: int = 32) -> list[tuple[list[str], float]]:
    """Enumerate simple paths in increasing cumulative-latency order.

    Best-first (Dijkstra-style) search over loopless paths guarantees that the
    first result is the lowest-latency path, independent of edge iteration order.
    """
    import heapq

    results: list[tuple[list[str], float]] = []
    heap: list[tuple[float, int, list[str]]] = [(0.0, 0, [src])]
    seq = 1
    while heap and len(results) < max_paths:
        latency, _, path = heapq.heappop(heap)
        node = path[-1]
        if node == dst:
            results.append((path, latency))
            continue
        if len(path) > cutoff:
            continue
        for neighbor, lat in adj.get(node, []):
            if neighbor in path:
                continue
            heapq.heappush(heap, (latency + lat, seq, path + [neighbor]))
            seq += 1
    return results


def get_alternative_paths(graph: GraphWrapper, source: str, destination: str) -> dict:
    for node_id in (source, destination):
        if not graph.node_exists(node_id):
            raise NodeNotFound(f"Node '{node_id}' not found")

    adj = _up_adjacency(graph)
    raw = _enumerate_paths(adj, source, destination)
    raw.sort(key=lambda p: (p[1], len(p[0])))

    min_latency = raw[0][1] if raw else None
    paths = []
    for path, latency in raw:
        paths.append({
            "path": path,
            "total_latency_ms": round(latency, 3),
            "total_hops": len(path),
            "is_active": min_latency is not None and abs(latency - min_latency) < 1e-9,
        })

    ecmp = sum(1 for p in paths if p["is_active"]) > 1
    return {
        "source": source,
        "destination": destination,
        "paths": paths,
        "ecmp_available": ecmp,
        "total_paths": len(paths),
    }
