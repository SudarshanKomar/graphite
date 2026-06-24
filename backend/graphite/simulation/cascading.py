"""Cascading effect computations.

Pure-ish helpers that apply the secondary effects of a mutation to the working
twin and return a description of every change made. The simulation engine is
responsible for primary validation, mutation logging, baseline restoration, and
service-health recomputation; these helpers handle the topological propagation.
"""

from __future__ import annotations

from ..twin.graph_wrapper import GraphWrapper


def _physical_link_pairs(graph: GraphWrapper, device_id: str):
    """Yield (neighbor, link_id) for each distinct physical link on the device."""
    seen: set[str] = set()
    for edge in graph.get_physical_links(device_id):
        link_id = edge.get("link_id")
        if link_id in seen:
            continue
        seen.add(link_id)
        yield edge["target"], link_id


def _set_link_status(graph: GraphWrapper, a: str, b: str, status: str) -> None:
    """Set both directions of the physical link between a and b."""
    if graph.has_edge(a, b, "physical_link"):
        graph.set_edge_attr(a, b, "physical_link", status=status)
    if graph.has_edge(b, a, "physical_link"):
        graph.set_edge_attr(b, a, "physical_link", status=status)


def _host_is_isolated(graph: GraphWrapper, device_id: str) -> bool:
    """True if a device has no up physical link to an up neighbour."""
    for neighbor in graph.get_physical_neighbors(device_id, only_up=True):
        if graph.get_node(neighbor).get("status") == "up":
            return False
    return True


class CascadingEffects:
    """Computes and applies secondary effects of mutations on the working twin."""

    # ------------------------------------------------------------------ #
    # Device
    # ------------------------------------------------------------------ #
    @staticmethod
    def device_disabled(graph: GraphWrapper, device_id: str) -> dict:
        links_disabled: list[str] = []
        for neighbor, link_id in _physical_link_pairs(graph, device_id):
            edge = graph.find_link_edge(device_id, neighbor)
            if edge and edge.get("status") == "up":
                _set_link_status(graph, device_id, neighbor, "down")
                links_disabled.append(link_id)

        bgp_peers_dropped = CascadingEffects._drop_bgp(graph, device_id)
        services_affected = [
            s["id"] for s in graph.get_services() if s.get("host_device") == device_id
        ]
        vlans_affected = CascadingEffects._vlans_losing_device(graph, device_id)

        return {
            "links_disabled": links_disabled,
            "services_affected": services_affected,
            "vlans_affected": vlans_affected,
            "bgp_peers_dropped": bgp_peers_dropped,
        }

    @staticmethod
    def device_enabled(graph: GraphWrapper, baseline: GraphWrapper, device_id: str) -> dict:
        """Restore links/BGP to baseline where both endpoints are up (Issue 8)."""
        links_restored: list[str] = []
        for neighbor, link_id in _physical_link_pairs(graph, device_id):
            base_edge = baseline.find_link_edge(device_id, neighbor)
            base_status = base_edge.get("status") if base_edge else "up"
            if base_status == "up" and graph.get_node(neighbor).get("status") == "up":
                _set_link_status(graph, device_id, neighbor, "up")
                links_restored.append(link_id)

        bgp_peers_restored = CascadingEffects._restore_bgp(graph, baseline, device_id)
        services_restored = [
            s["id"] for s in graph.get_services() if s.get("host_device") == device_id
        ]
        return {
            "links_restored": links_restored,
            "services_restored": services_restored,
            "bgp_peers_restored": bgp_peers_restored,
        }

    # ------------------------------------------------------------------ #
    # Link
    # ------------------------------------------------------------------ #
    @staticmethod
    def link_disabled(graph: GraphWrapper, source: str, target: str) -> dict:
        _set_link_status(graph, source, target, "down")
        from ..analysis.path import get_alternative_paths
        alt = get_alternative_paths(graph, source, target)
        has_alt = any(
            p for p in alt["paths"]
            if not (len(p["path"]) == 2 and p["path"] == [source, target])
        )
        segments_isolated = []
        if not has_alt:
            # Whichever endpoint can no longer reach the other is "isolated".
            if not _reachable(graph, target, source):
                segments_isolated = [target]
        return {
            "segments_isolated": segments_isolated,
            "alternative_paths_available": has_alt,
        }

    @staticmethod
    def link_enabled(graph: GraphWrapper, source: str, target: str) -> dict:
        _set_link_status(graph, source, target, "up")
        return {"connectivity_restored_to": [target]}

    # ------------------------------------------------------------------ #
    # VLAN
    # ------------------------------------------------------------------ #
    @staticmethod
    def vlan_removed(graph: GraphWrapper, vlan_node_id: str) -> dict:
        devices = list(graph.get_vlan_devices(vlan_node_id))
        user_groups = []
        for grp in graph.get_vlan_user_groups(vlan_node_id):
            user_groups.append({
                "id": grp["id"],
                "name": grp.get("name"),
                "estimated_users": grp.get("estimated_users", 0),
            })
        # Remove carries_vlan edges and the serves edge; keep belongs_to + node.
        for dev in devices:
            graph.remove_edge(dev, vlan_node_id, "carries_vlan")
        for grp in user_groups:
            graph.remove_edge(vlan_node_id, grp["id"], "serves")
        graph.set_node_attr(vlan_node_id, status="removed")
        return {
            "devices_unconfigured": sorted(devices),
            "user_groups_disconnected": user_groups,
            "total_users_affected": sum(g["estimated_users"] for g in user_groups),
        }

    # ------------------------------------------------------------------ #
    # BGP
    # ------------------------------------------------------------------ #
    @staticmethod
    def bgp_peer_disabled(graph: GraphWrapper, device_id: str, peer_ip: str) -> dict:
        """Set a peer (and its reciprocal entry) to idle, withdrawing prefixes."""
        withdrawn: list[str] = []
        local = graph.get_node(device_id).get("bgp_state")
        peer_device = None
        if local:
            for peer in local.get("peers", []):
                if peer.get("peer_ip") == peer_ip:
                    peer["state"] = "idle"
                    withdrawn.extend(peer.get("prefixes_received", []))
                    peer_device = peer.get("peer_device")
            graph.set_node_attr(device_id, bgp_state=local)

        # Reciprocal side.
        if peer_device:
            remote = graph.get_node(peer_device).get("bgp_state")
            if remote:
                for peer in remote.get("peers", []):
                    if peer.get("peer_device") == device_id:
                        peer["state"] = "idle"
                graph.set_node_attr(peer_device, bgp_state=remote)

        return {
            "peer_device": peer_device,
            "prefixes_withdrawn": withdrawn,
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _drop_bgp(graph: GraphWrapper, device_id: str) -> list[str]:
        dropped: list[str] = []
        local = graph.get_node(device_id).get("bgp_state")
        if not local:
            return dropped
        for peer in local.get("peers", []):
            if peer.get("state") == "established":
                peer["state"] = "idle"
            peer_device = peer.get("peer_device")
            dropped.append(f"{device_id} <-> {peer_device} (AS{peer.get('peer_as')})")
            if peer_device and graph.node_exists(peer_device):
                remote = graph.get_node(peer_device).get("bgp_state")
                if remote:
                    for rp in remote.get("peers", []):
                        if rp.get("peer_device") == device_id:
                            rp["state"] = "idle"
                    graph.set_node_attr(peer_device, bgp_state=remote)
        graph.set_node_attr(device_id, bgp_state=local)
        return dropped

    @staticmethod
    def _restore_bgp(graph: GraphWrapper, baseline: GraphWrapper, device_id: str) -> list[str]:
        restored: list[str] = []
        local = graph.get_node(device_id).get("bgp_state")
        if not local:
            return restored
        for peer in local.get("peers", []):
            peer_device = peer.get("peer_device")
            if peer_device and graph.node_exists(peer_device) \
                    and graph.get_node(peer_device).get("status") == "up":
                peer["state"] = "established"
                restored.append(f"{device_id} <-> {peer_device}")
                remote = graph.get_node(peer_device).get("bgp_state")
                if remote:
                    for rp in remote.get("peers", []):
                        if rp.get("peer_device") == device_id:
                            rp["state"] = "established"
                    graph.set_node_attr(peer_device, bgp_state=remote)
        graph.set_node_attr(device_id, bgp_state=local)
        return restored

    @staticmethod
    def _vlans_losing_device(graph: GraphWrapper, device_id: str) -> list[str]:
        affected = []
        for vlan in graph.get_vlans():
            carriers = graph.get_vlan_devices(vlan["id"])
            if device_id not in carriers:
                continue
            up_carriers = [c for c in carriers
                           if c != device_id and graph.get_node(c).get("status") == "up"]
            if not up_carriers:
                affected.append(vlan["id"])
        return affected


def _reachable(graph: GraphWrapper, src: str, dst: str) -> bool:
    from collections import deque
    seen = {src}
    queue = deque([src])
    while queue:
        node = queue.popleft()
        if node == dst:
            return True
        for neighbor in graph.get_physical_neighbors(node, only_up=True):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return dst in seen
