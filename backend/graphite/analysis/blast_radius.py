"""Blast radius computation.

Computes the full impact of a failed/removed component (device, VLAN, service,
or link) on devices, services, and user populations, then derives a severity
rating from the thresholds in ``specs/schemas/tool-schemas.md``.
"""

from __future__ import annotations

from typing import Optional

from ..errors import ComponentNotFound, ServiceNotFound
from ..twin.graph_wrapper import GraphWrapper


def get_service_dependencies(graph: GraphWrapper, service_id: str) -> dict:
    """Return the dependency graph for a service (direct + transitive + dependents)."""
    if not graph.node_exists(service_id) or graph.get_node_type(service_id) != "service":
        raise ServiceNotFound(f"Service '{service_id}' not found")

    svc = graph.get_node(service_id)
    host = graph.get_service_host(service_id)
    host_status = graph.get_node(host).get("status") if host else None

    direct_ids = graph.get_service_deps(service_id)
    direct = [_svc_brief(graph, d) for d in direct_ids]

    # BFS for transitive dependencies with depth tracking.
    transitive = []
    seen = set(direct_ids) | {service_id}
    frontier = [(d, 1) for d in direct_ids]
    while frontier:
        current, depth = frontier.pop(0)
        for dep in graph.get_service_deps(current):
            if dep not in seen:
                seen.add(dep)
                brief = _svc_brief(graph, dep)
                brief["depth"] = depth + 1
                transitive.append(brief)
                frontier.append((dep, depth + 1))

    dependents = [{"id": d, "name": graph.get_node(d).get("name")}
                  for d in graph.get_service_dependents(service_id)]

    return {
        "service_id": service_id,
        "service_name": svc.get("name"),
        "status": svc.get("status"),
        "host_device": host,
        "host_device_status": host_status,
        "site": svc.get("site"),
        "direct_dependencies": direct,
        "transitive_dependencies": transitive,
        "dependent_services": dependents,
    }


def _svc_brief(graph: GraphWrapper, service_id: str) -> dict:
    node = graph.get_node(service_id)
    return {"id": service_id, "name": node.get("name"), "status": node.get("status")}


def get_blast_radius(graph: GraphWrapper, component_id: str) -> dict:
    component_type, payload = _classify(graph, component_id)
    if component_type is None:
        raise ComponentNotFound(f"Component '{component_id}' not found")

    if component_type == "device":
        result = _device_blast(graph, component_id)
    elif component_type == "vlan":
        result = _vlan_blast(graph, component_id)
    elif component_type == "service":
        result = _service_blast(graph, component_id)
    else:  # link
        result = _link_blast(graph, component_id, payload)

    affected_users = result["total_users_affected"]
    criticality = {svc["id"]: svc.get("criticality") for svc in graph.get_services()}
    severity, factors = _compute_severity(
        affected_users, result["affected_services"], criticality
    )
    result["severity"] = severity
    result["severity_factors"] = factors
    result["component_id"] = component_id
    result["component_type"] = component_type
    return result


# ---------------------------------------------------------------------------
# Component classification
# ---------------------------------------------------------------------------
def _classify(graph: GraphWrapper, component_id: str):
    if graph.node_exists(component_id):
        return graph.get_node_type(component_id), None
    edge = graph.find_edge_by_link_id(component_id)
    if edge is not None:
        return "link", edge
    return None, None


# ---------------------------------------------------------------------------
# Service dependency helpers
# ---------------------------------------------------------------------------
def _transitive_dependents(graph: GraphWrapper, service_ids: set[str]) -> set[str]:
    """All services that (transitively) depend on any service in the set."""
    result: set[str] = set()
    frontier = set(service_ids)
    while frontier:
        nxt: set[str] = set()
        for svc in frontier:
            for dep in graph.get_service_dependents(svc):
                if dep not in result and dep not in service_ids:
                    result.add(dep)
                    nxt.add(dep)
        frontier = nxt
    return result


def _services_on_devices(graph: GraphWrapper, device_ids: set[str]) -> set[str]:
    down = set()
    for svc in graph.get_services():
        if svc.get("host_device") in device_ids:
            down.add(svc["id"])
    return down


# ---------------------------------------------------------------------------
# Device blast
# ---------------------------------------------------------------------------
def _isolated_neighbors(graph: GraphWrapper, device_id: str) -> set[str]:
    """Single-homed neighbours that lose all connectivity if device_id is removed."""
    isolated = set()
    for neighbor in graph.get_physical_neighbors(device_id):
        up_links = [
            n for n in graph.get_physical_neighbors(neighbor, only_up=True)
            if n != device_id and graph.get_node(n).get("status") == "up"
        ]
        if not up_links:
            isolated.add(neighbor)
    return isolated


def _device_blast(graph: GraphWrapper, device_id: str) -> dict:
    isolated = _isolated_neighbors(graph, device_id)
    down_devices = {device_id} | isolated

    services_down = _services_on_devices(graph, down_devices)
    services_degraded = _transitive_dependents(graph, services_down)

    affected_devices = [{
        "id": device_id,
        "name": graph.get_node(device_id).get("name"),
        "impact": "down",
    }]
    for dev in sorted(isolated):
        affected_devices.append({
            "id": dev,
            "name": graph.get_node(dev).get("name"),
            "impact": "isolated",
        })

    affected_services = _build_service_impacts(graph, services_down, services_degraded)

    # V1 path: VLAN-wide user groups (only triggers when entire VLAN loses carriers).
    affected_user_groups, total_users = _user_groups_for_devices(graph, {device_id})

    # V2.1 path: locality-aware endpoint groups served by the failed device(s).
    ep_groups, ep_users = _endpoint_groups_for_devices(graph, down_devices)
    affected_user_groups += ep_groups
    total_users += ep_users

    return {
        "status": graph.get_node(device_id).get("status"),
        "affected_devices": affected_devices,
        "affected_services": affected_services,
        "affected_user_groups": affected_user_groups,
        "total_users_affected": total_users,
    }


def _endpoint_groups_for_devices(graph: GraphWrapper, device_ids: set[str]):
    """V2.1: Endpoint groups directly served by any device in the set.

    Uses the ``serves_zone`` graph relationship (device → endpoint_group).
    This captures localized impact: AP failure → floor zone outage, access
    switch failure → floor wired/wireless outage, etc.
    """
    affected = []
    total = 0
    seen: set[str] = set()
    for dev_id in device_ids:
        for grp in graph.get_zones_served_by(dev_id):
            gid = grp["id"]
            if gid in seen:
                continue
            seen.add(gid)
            users = grp.get("estimated_users", 0)
            affected.append({
                "id": gid,
                "name": grp.get("name"),
                "estimated_users": users,
                "impact": "disconnected",
            })
            total += users
    return affected, total


def _user_groups_for_devices(graph: GraphWrapper, device_ids: set[str]):
    """User groups whose VLAN is solely carried by one of device_ids."""
    affected = []
    total = 0
    for vlan in graph.get_vlans():
        carriers = set(graph.get_vlan_devices(vlan["id"]))
        if not carriers:
            continue
        up_carriers = {d for d in carriers
                       if graph.get_node(d).get("status") == "up"}
        # VLAN lost if its only up carriers are within device_ids.
        if up_carriers and up_carriers.issubset(device_ids):
            for grp in _groups_for_vlan(graph, vlan):
                affected.append({
                    "id": grp["id"],
                    "name": grp.get("name"),
                    "estimated_users": grp.get("estimated_users", 0),
                    "impact": "disconnected",
                })
                total += grp.get("estimated_users", 0)
    return affected, total


# ---------------------------------------------------------------------------
# VLAN blast
# ---------------------------------------------------------------------------
def _groups_for_vlan(graph: GraphWrapper, vlan_node: dict) -> list[dict]:
    """User groups matching a VLAN by (vlan_id, site) — edge-independent."""
    groups = []
    for grp in graph.get_user_groups(site=vlan_node.get("site")):
        if grp.get("vlan_id") == vlan_node.get("vlan_id"):
            groups.append(grp)
    return groups


def _vlan_blast(graph: GraphWrapper, vlan_node_id: str) -> dict:
    vlan = graph.get_node(vlan_node_id)
    groups = _groups_for_vlan(graph, vlan)

    affected_user_groups = []
    total_users = 0
    for grp in groups:
        affected_user_groups.append({
            "id": grp["id"],
            "name": grp.get("name"),
            "estimated_users": grp.get("estimated_users", 0),
            "impact": "disconnected",
        })
        total_users += grp.get("estimated_users", 0)

    carriers = graph.get_vlan_devices(vlan_node_id)
    affected_devices = [{
        "id": d,
        "name": graph.get_node(d).get("name"),
        "impact": "degraded",
    } for d in sorted(carriers)]

    return {
        "status": vlan.get("status"),
        "affected_devices": affected_devices,
        "affected_services": [],
        "affected_user_groups": affected_user_groups,
        "total_users_affected": total_users,
    }


# ---------------------------------------------------------------------------
# Service blast
# ---------------------------------------------------------------------------
def _service_blast(graph: GraphWrapper, service_id: str) -> dict:
    services_down = {service_id}
    services_degraded = _transitive_dependents(graph, services_down)
    affected_services = _build_service_impacts(graph, services_down, services_degraded)
    return {
        "status": graph.get_node(service_id).get("status"),
        "affected_devices": [],
        "affected_services": affected_services,
        "affected_user_groups": [],
        "total_users_affected": 0,
    }


# ---------------------------------------------------------------------------
# Link blast
# ---------------------------------------------------------------------------
def _link_blast(graph: GraphWrapper, link_id: str, edge) -> dict:
    src, dst, data = edge
    # Determine whether an alternative path exists between the endpoints.
    from .path import get_alternative_paths

    alt = get_alternative_paths(graph, src, dst)
    has_alt = any(
        p for p in alt["paths"]
        if not (len(p["path"]) == 2 and p["path"][0] == src and p["path"][1] == dst)
    )

    impact = "degraded" if has_alt else "isolated"
    affected_devices = [
        {"id": src, "name": graph.get_node(src).get("name"), "impact": impact},
        {"id": dst, "name": graph.get_node(dst).get("name"), "impact": impact},
    ]
    return {
        "status": data.get("status"),
        "affected_devices": affected_devices,
        "affected_services": [],
        "affected_user_groups": [],
        "total_users_affected": 0,
    }


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------
def _build_service_impacts(graph: GraphWrapper, down: set[str],
                           degraded: set[str]) -> list[dict]:
    impacts = []
    for svc_id in sorted(down):
        impacts.append({
            "id": svc_id,
            "name": graph.get_node(svc_id).get("name"),
            "impact": "down",
            "reason": "Host device or component unavailable",
        })
    for svc_id in sorted(degraded):
        deps = [d for d in graph.get_service_deps(svc_id) if d in down or d in degraded]
        impacts.append({
            "id": svc_id,
            "name": graph.get_node(svc_id).get("name"),
            "impact": "degraded",
            "reason": f"Depends on impacted service(s): {', '.join(sorted(deps))}",
        })
    return impacts


def _compute_severity(affected_users: int, affected_services: list[dict],
                      criticality: dict[str, str]) -> tuple[str, list[str]]:
    factors: list[str] = []

    has_critical_down = any(
        s["impact"] == "down" and criticality.get(s["id"]) == "critical"
        for s in affected_services
    )
    has_high = any(
        criticality.get(s["id"]) in ("critical", "high")
        for s in affected_services
    )
    has_medium = any(
        criticality.get(s["id"]) == "medium" for s in affected_services
    )

    if affected_users > 1000:
        factors.append(f"{affected_users} users affected (exceeds critical threshold of 1000)")
    if has_critical_down:
        factors.append("A critical service is down")

    if affected_users > 1000 or has_critical_down:
        severity = "critical"
    elif affected_users > 100 or has_high:
        severity = "high"
        if affected_users > 100:
            factors.append(f"{affected_users} users affected (exceeds high threshold of 100)")
        if has_high:
            factors.append("A high-criticality service is affected")
    elif affected_users > 10 or has_medium:
        severity = "medium"
        factors.append(f"{affected_users} users affected" if affected_users > 10
                       else "A medium-criticality service is affected")
    else:
        severity = "low"
        factors.append("Limited user and service impact")
    return severity, factors
