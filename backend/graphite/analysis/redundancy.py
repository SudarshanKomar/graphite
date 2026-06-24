"""Redundancy analysis: redundancy status, single points of failure, failover.

These use connectivity over *up* physical links. A device/link is a single
point of failure (SPOF) if removing it disconnects some device from the site's
WAN exit (its edge routers). Site sizes are small (~15 devices) so the
remove-and-test approach (O(n^2)) is acceptable per audit finding L2.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from ..errors import ComponentNotFound, SiteNotFound
from ..twin.graph_wrapper import GraphWrapper
from .path import _up_adjacency, get_alternative_paths


def _bfs_reachable(adj: dict[str, list[tuple[str, float]]], sources: set[str]) -> set[str]:
    seen = set(sources)
    queue = deque(sources)
    while queue:
        node = queue.popleft()
        for neighbor, _ in adj.get(node, []):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return seen


def _adj_without_node(adj, node: str):
    return {
        src: [(d, l) for d, l in dsts if d != node]
        for src, dsts in adj.items() if src != node
    }


def _adj_without_edge(adj, a: str, b: str):
    out = {}
    for src, dsts in adj.items():
        filtered = []
        for d, l in dsts:
            if (src == a and d == b) or (src == b and d == a):
                continue
            filtered.append((d, l))
        out[src] = filtered
    return out


def _site_anchor_devices(graph: GraphWrapper, site: str) -> set[str]:
    routers = {d["id"] for d in graph.get_devices(site=site, device_type="router")}
    if routers:
        return routers
    return {d["id"] for d in graph.get_devices(site=site, device_type="core_switch")}


# ---------------------------------------------------------------------------
# get_single_points_of_failure
# ---------------------------------------------------------------------------
def get_single_points_of_failure(graph: GraphWrapper, site: str) -> dict:
    if not graph.node_exists(f"site-{site}"):
        raise SiteNotFound(f"Site '{site}' not found")

    site_devices = {d["id"] for d in graph.get_devices(site=site)}
    anchors = _site_anchor_devices(graph, site)
    adj = _up_adjacency(graph)

    baseline_reach = _bfs_reachable(adj, anchors) & site_devices
    spofs: list[dict] = []

    # Device SPOFs.
    for dev in sorted(site_devices - anchors):
        reach = _bfs_reachable(_adj_without_node(adj, dev), anchors) & site_devices
        lost = baseline_reach - reach - {dev}
        if lost:
            spofs.append({
                "component_id": dev,
                "component_type": graph.get_node(dev).get("device_type", "device"),
                "failure_impact": (
                    f"Removing {dev} isolates: {', '.join(sorted(lost))}"
                ),
            })

    # Link SPOFs (within-site links only, each undirected pair once).
    seen_pairs: set[frozenset] = set()
    for src, dst, data in graph.get_edges_by_relation("physical_link"):
        if data.get("status") != "up":
            continue
        if src not in site_devices or dst not in site_devices:
            continue
        pair = frozenset((src, dst))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        reach = _bfs_reachable(_adj_without_edge(adj, src, dst), anchors) & site_devices
        lost = baseline_reach - reach
        if lost:
            spofs.append({
                "component_id": data.get("link_id"),
                "component_type": "link",
                "failure_impact": f"Removing link {data.get('link_id')} isolates: "
                                  f"{', '.join(sorted(lost))}",
            })

    total = len(spofs)
    risk = "low" if total == 0 else "medium" if total <= 2 else "high"
    return {
        "site": site,
        "single_points_of_failure": spofs,
        "total_spofs": total,
        "risk_level": risk,
    }


# ---------------------------------------------------------------------------
# get_redundancy_status
# ---------------------------------------------------------------------------
def get_redundancy_status(graph: GraphWrapper, component_id: str) -> dict:
    if graph.node_exists(component_id) and graph.get_node_type(component_id) == "device":
        return _device_redundancy(graph, component_id)

    edge = graph.find_edge_by_link_id(component_id)
    if edge is not None:
        return _link_redundancy(graph, component_id, edge)

    raise ComponentNotFound(f"Component '{component_id}' not found")


def _device_redundancy(graph: GraphWrapper, device_id: str) -> dict:
    site = graph.get_node(device_id).get("site")
    anchors = _site_anchor_devices(graph, site)
    site_devices = {d["id"] for d in graph.get_devices(site=site)}
    adj = _up_adjacency(graph)

    baseline_reach = _bfs_reachable(adj, anchors) & site_devices
    reach_without = _bfs_reachable(_adj_without_node(adj, device_id), anchors) & site_devices
    lost = baseline_reach - reach_without - {device_id}

    parallel_links = len(graph.get_physical_links(device_id, only_up=True))
    is_spof = bool(lost) and device_id not in anchors
    has_redundancy = not is_spof

    return {
        "component_id": device_id,
        "component_type": graph.get_node(device_id).get("device_type", "device"),
        "has_redundancy": has_redundancy,
        "redundancy_details": {
            "parallel_links": parallel_links,
            "alternative_paths": 0 if is_spof else 1,
            "failover_available": has_redundancy,
            "ecmp_enabled": parallel_links >= 2,
        },
        "risk_assessment": "single_point_of_failure" if is_spof
                           else "low_risk" if parallel_links < 2 else "no_risk",
    }


def _link_redundancy(graph: GraphWrapper, link_id: str, edge) -> dict:
    src, dst, _data = edge
    parallel = len(graph.get_edges(src, dst, relation="physical_link"))
    alt = get_alternative_paths(graph, src, dst)
    alt_paths = [
        p for p in alt["paths"]
        if not (len(p["path"]) == 2 and p["path"] == [src, dst])
    ]
    has_redundancy = parallel > 1 or len(alt_paths) > 0
    return {
        "component_id": link_id,
        "component_type": "link",
        "has_redundancy": has_redundancy,
        "redundancy_details": {
            "parallel_links": parallel,
            "alternative_paths": len(alt_paths),
            "failover_available": len(alt_paths) > 0,
            "ecmp_enabled": parallel > 1,
        },
        "risk_assessment": "no_risk" if has_redundancy else "single_point_of_failure",
    }


# ---------------------------------------------------------------------------
# get_failover_path
# ---------------------------------------------------------------------------
def get_failover_path(graph: GraphWrapper, primary_component: str) -> dict:
    # Link form "source:target".
    if ":" in primary_component and not graph.node_exists(primary_component):
        src, dst = primary_component.split(":", 1)
        return _failover_for_link(graph, primary_component, src, dst)

    # Link id.
    edge = graph.find_edge_by_link_id(primary_component)
    if edge is not None:
        src, dst, _ = edge
        return _failover_for_link(graph, primary_component, src, dst)

    # Device.
    if graph.node_exists(primary_component) and \
            graph.get_node_type(primary_component) == "device":
        return _failover_for_device(graph, primary_component)

    raise ComponentNotFound(f"Component '{primary_component}' not found")


def _failover_for_link(graph: GraphWrapper, label: str, src: str, dst: str) -> dict:
    if not graph.node_exists(src) or not graph.node_exists(dst):
        raise ComponentNotFound(f"Endpoint of '{label}' not found")
    direct = graph.find_link_edge(src, dst)
    primary_latency = float(direct.get("latency_ms")) if direct else None

    adj = _adj_without_edge(_up_adjacency(graph), src, dst)
    from .path import _enumerate_paths
    paths = _enumerate_paths(adj, src, dst)
    paths.sort(key=lambda p: (p[1], len(p[0])))
    if not paths:
        return {
            "primary_component": label,
            "failover_available": False,
            "failover_path": None,
            "failover_latency_ms": None,
            "latency_increase_ms": None,
        }
    best_path, best_latency = paths[0]
    return {
        "primary_component": label,
        "failover_available": True,
        "failover_path": best_path,
        "failover_latency_ms": round(best_latency, 3),
        "latency_increase_ms": (round(best_latency - primary_latency, 3)
                                if primary_latency is not None else None),
    }


def _failover_for_device(graph: GraphWrapper, device_id: str) -> dict:
    status = _device_redundancy(graph, device_id)
    return {
        "primary_component": device_id,
        "failover_available": status["has_redundancy"],
        "failover_path": None,
        "failover_latency_ms": None,
        "latency_increase_ms": None,
    }
