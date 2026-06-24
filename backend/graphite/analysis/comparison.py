"""Diff the working twin against the baseline to surface applied mutations.

Returns a list of structured changes whose ``change_type`` values match the
set documented for ``compare_with_baseline`` in
``specs/schemas/tool-schemas.md``.
"""

from __future__ import annotations

from ..twin.graph_wrapper import GraphWrapper


def compare_with_baseline(working: GraphWrapper, baseline: GraphWrapper) -> dict:
    changes: list[dict] = []

    _diff_nodes(working, baseline, changes)
    _diff_links(working, baseline, changes)

    return {"mutations_applied": len(changes), "changes": changes}


def _change(change_type: str, component_id: str, field: str,
            baseline_value, current_value) -> dict:
    return {
        "change_type": change_type,
        "component_id": component_id,
        "field": field,
        "baseline_value": baseline_value,
        "current_value": current_value,
    }


def _diff_nodes(working: GraphWrapper, baseline: GraphWrapper, changes: list[dict]) -> None:
    base_ids = set(baseline.all_nodes())
    work_ids = set(working.all_nodes())

    # Nodes added to the working twin (e.g. add_vlan with a brand-new node).
    for node_id in work_ids - base_ids:
        node = working.get_node(node_id)
        if node.get("node_type") == "vlan":
            changes.append(_change("vlan_added", node_id, "status", None,
                                   node.get("status")))

    for node_id in base_ids & work_ids:
        b = baseline.get_node(node_id)
        w = working.get_node(node_id)
        ntype = b.get("node_type")
        if ntype == "device":
            _diff_device(node_id, b, w, changes)
        elif ntype == "vlan":
            _diff_vlan(node_id, b, w, changes)


def _diff_device(node_id: str, b: dict, w: dict, changes: list[dict]) -> None:
    if b.get("status") != w.get("status"):
        changes.append(_change("device_status", node_id, "status",
                               b.get("status"), w.get("status")))

    _diff_routes(node_id, b.get("routes", []), w.get("routes", []), changes)
    _diff_bgp(node_id, b.get("bgp_state"), w.get("bgp_state"), changes)


def _route_key(route: dict):
    return (route.get("prefix"), route.get("next_hop"))


def _diff_routes(node_id: str, base_routes: list[dict], work_routes: list[dict],
                 changes: list[dict]) -> None:
    base_keys = {_route_key(r) for r in base_routes}
    work_keys = {_route_key(r) for r in work_routes}
    for key in work_keys - base_keys:
        changes.append(_change("route_added", node_id, "routes", None,
                               {"prefix": key[0], "next_hop": key[1]}))
    for key in base_keys - work_keys:
        changes.append(_change("route_removed", node_id, "routes",
                               {"prefix": key[0], "next_hop": key[1]}, None))


def _diff_bgp(node_id: str, base_bgp, work_bgp, changes: list[dict]) -> None:
    if not base_bgp and not work_bgp:
        return
    base_peers = {p["peer_ip"]: p for p in (base_bgp or {}).get("peers", [])}
    work_peers = {p["peer_ip"]: p for p in (work_bgp or {}).get("peers", [])}

    for peer_ip, bp in base_peers.items():
        wp = work_peers.get(peer_ip)
        if wp is None:
            continue
        if bp.get("state") != wp.get("state"):
            changes.append(_change("bgp_peer_state", f"{node_id}:{peer_ip}", "state",
                                   bp.get("state"), wp.get("state")))
        base_adv = set(bp.get("prefixes_advertised", []))
        work_adv = set(wp.get("prefixes_advertised", []))
        for prefix in base_adv - work_adv:
            changes.append(_change("prefix_withdrawn", f"{node_id}:{peer_ip}",
                                   "prefixes_advertised", prefix, None))
        for prefix in work_adv - base_adv:
            changes.append(_change("prefix_advertised", f"{node_id}:{peer_ip}",
                                   "prefixes_advertised", None, prefix))


def _diff_vlan(node_id: str, b: dict, w: dict, changes: list[dict]) -> None:
    if b.get("status") != w.get("status"):
        change_type = "vlan_removed" if w.get("status") == "removed" else "vlan_added"
        changes.append(_change(change_type, node_id, "status",
                               b.get("status"), w.get("status")))


def _diff_links(working: GraphWrapper, baseline: GraphWrapper, changes: list[dict]) -> None:
    # Dedup by link_id; compare status and latency.
    seen: set[str] = set()
    for src, dst, b_data in baseline.get_edges_by_relation("physical_link"):
        link_id = b_data.get("link_id")
        if link_id in seen:
            continue
        seen.add(link_id)
        w_edges = working.get_edges(src, dst, relation="physical_link")
        if not w_edges:
            continue
        w_data = w_edges[0]
        if b_data.get("status") != w_data.get("status"):
            changes.append(_change("link_status", link_id, "status",
                                   b_data.get("status"), w_data.get("status")))
        if b_data.get("latency_ms") != w_data.get("latency_ms"):
            changes.append(_change("link_latency", link_id, "latency_ms",
                                   b_data.get("latency_ms"), w_data.get("latency_ms")))
