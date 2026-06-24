"""SimulationEngine — applies mutations to the working twin.

Each mutation method validates preconditions, applies primary + cascading
changes via :class:`CascadingEffects`, records a :class:`MutationRecord`, then
recomputes service health (spec-refinements Issue 2). The baseline twin is never
touched.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from datetime import datetime, timezone

from ..errors import (
    DeviceAlreadyDown,
    DeviceAlreadyUp,
    DeviceDown,
    DeviceNotFound,
    InvalidLatency,
    InvalidNextHop,
    LinkAlreadyDown,
    LinkAlreadyUp,
    LinkNotFound,
    PeerAlreadyDown,
    PeerAlreadyUp,
    PeerNotFound,
    PrefixAlreadyAdvertised,
    PrefixNotFound,
    RouteConflict,
    RouteNotFound,
    SiteNotFound,
    VlanAlreadyExists,
    VlanAlreadyRemoved,
    VlanNotFound,
)
from ..twin.graph_wrapper import GraphWrapper
from ..twin.manager import TwinManager
from .cascading import CascadingEffects, _host_is_isolated

_SITE_PREFIX = {"bangalore": "blr", "london": "lon", "newyork": "nyc", "singapore": "sg"}


@dataclass
class MutationRecord:
    timestamp: str
    mutation_type: str
    parameters: dict
    cascading_effects: dict


class SimulationEngine:
    """Applies mutations to the working twin with cascading effects."""

    def __init__(self, twin_manager: TwinManager):
        self._twin_manager = twin_manager
        self._mutation_log: list[MutationRecord] = []

    # ------------------------------------------------------------------ #
    # Graph access
    # ------------------------------------------------------------------ #
    @property
    def graph(self) -> GraphWrapper:
        return self._twin_manager.working_wrapper

    @property
    def _baseline(self) -> GraphWrapper:
        return self._twin_manager.baseline_wrapper

    def _require_device(self, device_id: str) -> dict:
        if not self.graph.node_exists(device_id) or \
                self.graph.get_node_type(device_id) != "device":
            raise DeviceNotFound(f"Device '{device_id}' not found")
        return self.graph.get_node(device_id)

    # ------------------------------------------------------------------ #
    # Device mutations
    # ------------------------------------------------------------------ #
    def disable_device(self, device_id: str) -> dict:
        node = self._require_device(device_id)
        if node.get("status") == "down":
            raise DeviceAlreadyDown(f"Device '{device_id}' is already down")

        self.graph.set_node_attr(device_id, status="down")
        effects = CascadingEffects.device_disabled(self.graph, device_id)
        self._finalize("disable_device", {"device_id": device_id}, effects)
        return {
            "device_id": device_id,
            "previous_status": "up",
            "new_status": "down",
            "cascading_effects": effects,
        }

    def enable_device(self, device_id: str) -> dict:
        node = self._require_device(device_id)
        if node.get("status") == "up":
            raise DeviceAlreadyUp(f"Device '{device_id}' is already up")

        self.graph.set_node_attr(device_id, status="up")
        effects = CascadingEffects.device_enabled(self.graph, self._baseline, device_id)
        self._finalize("enable_device", {"device_id": device_id}, effects)
        return {
            "device_id": device_id,
            "previous_status": "down",
            "new_status": "up",
            "restored": effects,
        }

    # ------------------------------------------------------------------ #
    # Link mutations
    # ------------------------------------------------------------------ #
    def disable_link(self, source: str, target: str) -> dict:
        edge = self.graph.find_link_edge(source, target)
        if edge is None:
            raise LinkNotFound(f"No link between '{source}' and '{target}'")
        if edge.get("status") == "down":
            raise LinkAlreadyDown(f"Link '{source}'-'{target}' is already down")

        effects = CascadingEffects.link_disabled(self.graph, source, target)
        self._finalize("disable_link", {"source": source, "target": target}, effects)
        return {
            "link_id": edge.get("link_id"),
            "previous_status": "up",
            "new_status": "down",
            "cascading_effects": effects,
        }

    def enable_link(self, source: str, target: str) -> dict:
        edge = self.graph.find_link_edge(source, target)
        if edge is None:
            raise LinkNotFound(f"No link between '{source}' and '{target}'")
        if edge.get("status") == "up":
            raise LinkAlreadyUp(f"Link '{source}'-'{target}' is already up")
        for endpoint in (source, target):
            if self.graph.get_node(endpoint).get("status") == "down":
                raise DeviceDown(f"Cannot enable link — device '{endpoint}' is down")

        effects = CascadingEffects.link_enabled(self.graph, source, target)
        self._finalize("enable_link", {"source": source, "target": target}, effects)
        return {
            "link_id": edge.get("link_id"),
            "previous_status": "down",
            "new_status": "up",
            "restored": effects,
        }

    def set_link_latency(self, source: str, target: str, latency_ms: float) -> dict:
        edge = self.graph.find_link_edge(source, target)
        if edge is None:
            raise LinkNotFound(f"No link between '{source}' and '{target}'")
        if latency_ms <= 0:
            raise InvalidLatency("Latency must be positive")

        previous = edge.get("latency_ms")
        # Update both directions.
        self.graph.set_edge_attr(source, target, "physical_link", latency_ms=latency_ms)
        if self.graph.has_edge(target, source, "physical_link"):
            self.graph.set_edge_attr(target, source, "physical_link", latency_ms=latency_ms)

        effects = {"previous_latency_ms": previous, "new_latency_ms": latency_ms}
        self._finalize("set_link_latency",
                       {"source": source, "target": target, "latency_ms": latency_ms},
                       effects)
        return {
            "link_id": edge.get("link_id"),
            "previous_latency_ms": previous,
            "new_latency_ms": latency_ms,
            "affected_paths": 1,
        }

    # ------------------------------------------------------------------ #
    # VLAN mutations
    # ------------------------------------------------------------------ #
    def remove_vlan(self, vlan_id: int, site: str) -> dict:
        vlan_node_id = self._vlan_node_id(site, vlan_id)
        if not self.graph.node_exists(vlan_node_id):
            raise VlanNotFound(f"VLAN {vlan_id} not found at site '{site}'")
        if self.graph.get_node(vlan_node_id).get("status") == "removed":
            raise VlanAlreadyRemoved(f"VLAN {vlan_id} at site '{site}' is already removed")

        effects = CascadingEffects.vlan_removed(self.graph, vlan_node_id)
        self._finalize("remove_vlan", {"vlan_id": vlan_id, "site": site}, effects)
        return {
            "vlan_node_id": vlan_node_id,
            "vlan_id": vlan_id,
            "site": site,
            "cascading_effects": {
                "devices_unconfigured": effects["devices_unconfigured"],
                "user_groups_disconnected": effects["user_groups_disconnected"],
                "total_users_affected": effects["total_users_affected"],
                "services_impacted": [],
            },
        }

    def add_vlan(self, vlan_id: int, site: str, subnet: str, name: str,
                 devices: list[str]) -> dict:
        if not self.graph.node_exists(f"site-{site}"):
            raise SiteNotFound(f"Site '{site}' not found")
        vlan_node_id = self._vlan_node_id(site, vlan_id)
        existing = self.graph.node_exists(vlan_node_id)
        if existing and self.graph.get_node(vlan_node_id).get("status") == "active":
            raise VlanAlreadyExists(f"VLAN {vlan_id} already active at site '{site}'")
        for dev in devices:
            if not self.graph.node_exists(dev):
                raise DeviceNotFound(f"Device '{dev}' not found")

        if not existing:
            self.graph.add_node(
                vlan_node_id, node_type="vlan", vlan_id=vlan_id, name=name,
                subnet=subnet, gateway=subnet.split("/")[0], site=site,
                status="active", description=None,
            )
            self.graph.add_edge(vlan_node_id, f"site-{site}", "belongs_to")
        else:
            self.graph.set_node_attr(vlan_node_id, status="active", subnet=subnet,
                                     name=name)

        for dev in devices:
            self.graph.add_edge(dev, vlan_node_id, "carries_vlan", tagged=True)

        # Re-establish serves edges to matching user groups.
        restored = []
        for grp in self.graph.get_user_groups(site=site):
            if grp.get("vlan_id") == vlan_id:
                self.graph.add_edge(vlan_node_id, grp["id"], "serves")
                restored.append(grp["id"])

        effects = {"devices_configured": devices, "connectivity_restored_to": restored}
        self._finalize("add_vlan",
                       {"vlan_id": vlan_id, "site": site, "subnet": subnet,
                        "name": name, "devices": devices}, effects)
        return {
            "vlan_node_id": vlan_node_id,
            "vlan_id": vlan_id,
            "site": site,
            "devices_configured": devices,
            "connectivity_restored_to": restored,
        }

    # ------------------------------------------------------------------ #
    # BGP mutations
    # ------------------------------------------------------------------ #
    def disable_bgp_peer(self, device_id: str, peer_ip: str) -> dict:
        node = self._require_device(device_id)
        peer = self._find_peer(node, peer_ip)
        if peer is None:
            raise PeerNotFound(f"No BGP peer {peer_ip} on device '{device_id}'")
        if peer.get("state") == "idle":
            raise PeerAlreadyDown(f"BGP peer {peer_ip} on '{device_id}' is already idle")

        peer_as = peer.get("peer_as")
        effects = CascadingEffects.bgp_peer_disabled(self.graph, device_id, peer_ip)
        self._finalize("disable_bgp_peer",
                       {"device_id": device_id, "peer_ip": peer_ip}, effects)
        return {
            "device_id": device_id,
            "peer_ip": peer_ip,
            "peer_as": peer_as,
            "previous_state": "established",
            "new_state": "idle",
            "cascading_effects": {
                "prefixes_withdrawn": effects["prefixes_withdrawn"],
                "routes_removed": len(effects["prefixes_withdrawn"]),
                "destinations_unreachable": effects["prefixes_withdrawn"],
            },
        }

    def enable_bgp_peer(self, device_id: str, peer_ip: str) -> dict:
        node = self._require_device(device_id)
        peer = self._find_peer(node, peer_ip)
        if peer is None:
            raise PeerNotFound(f"No BGP peer {peer_ip} on device '{device_id}'")
        if peer.get("state") == "established":
            raise PeerAlreadyUp(f"BGP peer {peer_ip} on '{device_id}' is already up")

        bgp = node.get("bgp_state")
        peer_device = None
        received = []
        advertised = []
        for p in bgp.get("peers", []):
            if p.get("peer_ip") == peer_ip:
                p["state"] = "established"
                peer_device = p.get("peer_device")
                received = p.get("prefixes_received", [])
                advertised = p.get("prefixes_advertised", [])
        self.graph.set_node_attr(device_id, bgp_state=bgp)
        if peer_device and self.graph.node_exists(peer_device):
            remote = self.graph.get_node(peer_device).get("bgp_state")
            if remote:
                for rp in remote.get("peers", []):
                    if rp.get("peer_device") == device_id:
                        rp["state"] = "established"
                self.graph.set_node_attr(peer_device, bgp_state=remote)

        effects = {"prefixes_received": received, "prefixes_advertised": advertised}
        self._finalize("enable_bgp_peer",
                       {"device_id": device_id, "peer_ip": peer_ip}, effects)
        return {
            "device_id": device_id,
            "peer_ip": peer_ip,
            "new_state": "established",
            "restored": {
                "prefixes_received": received,
                "prefixes_advertised": advertised,
                "routes_added": len(received),
            },
        }

    def withdraw_prefix(self, device_id: str, prefix: str) -> dict:
        node = self._require_device(device_id)
        bgp = node.get("bgp_state")
        if not bgp:
            raise PrefixNotFound(f"Device '{device_id}' has no BGP config")
        notified = []
        found = False
        for peer in bgp.get("peers", []):
            if prefix in peer.get("prefixes_advertised", []):
                peer["prefixes_advertised"].remove(prefix)
                notified.append(peer.get("peer_device"))
                found = True
        if not found:
            raise PrefixNotFound(f"Prefix {prefix} not advertised by '{device_id}'")
        self.graph.set_node_attr(device_id, bgp_state=bgp)
        effects = {"peers_notified": notified, "destinations_affected": [prefix]}
        self._finalize("withdraw_prefix",
                       {"device_id": device_id, "prefix": prefix}, effects)
        return {
            "device_id": device_id,
            "prefix": prefix,
            "peers_notified": notified,
            "cascading_effects": {"destinations_affected": [prefix]},
        }

    def advertise_prefix(self, device_id: str, prefix: str) -> dict:
        node = self._require_device(device_id)
        bgp = node.get("bgp_state")
        if not bgp:
            raise PrefixNotFound(f"Device '{device_id}' has no BGP config")
        notified = []
        for peer in bgp.get("peers", []):
            adv = peer.setdefault("prefixes_advertised", [])
            if prefix in adv:
                raise PrefixAlreadyAdvertised(
                    f"Prefix {prefix} already advertised to {peer.get('peer_device')}"
                )
            adv.append(prefix)
            notified.append(peer.get("peer_device"))
        self.graph.set_node_attr(device_id, bgp_state=bgp)
        effects = {"peers_notified": notified, "reachability_restored": [prefix]}
        self._finalize("advertise_prefix",
                       {"device_id": device_id, "prefix": prefix}, effects)
        return {
            "device_id": device_id,
            "prefix": prefix,
            "peers_notified": notified,
            "reachability_restored": [prefix],
        }

    # ------------------------------------------------------------------ #
    # Static route mutations
    # ------------------------------------------------------------------ #
    def add_static_route(self, device_id: str, prefix: str, next_hop: str) -> dict:
        node = self._require_device(device_id)
        try:
            ipaddress.ip_network(prefix, strict=False)
        except ValueError as exc:
            raise InvalidNextHop(f"Invalid prefix '{prefix}': {exc}") from exc
        if next_hop not in self.graph.get_physical_neighbors(device_id):
            raise InvalidNextHop(f"Next hop '{next_hop}' not directly connected")

        routes = list(node.get("routes", []))
        if any(r.get("prefix") == prefix for r in routes):
            raise RouteConflict(f"Route to {prefix} already exists")
        routes.append({
            "prefix": prefix, "next_hop": next_hop, "next_hop_ip": None,
            "protocol": "static", "metric": 1, "status": "active",
        })
        self.graph.set_node_attr(device_id, routes=routes)
        effects = {"route_added": {"prefix": prefix, "next_hop": next_hop,
                                   "protocol": "static"}}
        self._finalize("add_static_route",
                       {"device_id": device_id, "prefix": prefix, "next_hop": next_hop},
                       effects)
        return {
            "device_id": device_id,
            "route_added": effects["route_added"],
            "reachability_changes": [prefix],
        }

    def remove_static_route(self, device_id: str, prefix: str) -> dict:
        node = self._require_device(device_id)
        routes = list(node.get("routes", []))
        match = next((r for r in routes
                      if r.get("prefix") == prefix and r.get("protocol") == "static"), None)
        if match is None:
            raise RouteNotFound(f"No static route to {prefix} on '{device_id}'")
        routes.remove(match)
        self.graph.set_node_attr(device_id, routes=routes)
        effects = {"route_removed": {"prefix": prefix, "next_hop": match.get("next_hop")}}
        self._finalize("remove_static_route",
                       {"device_id": device_id, "prefix": prefix}, effects)
        return {
            "device_id": device_id,
            "route_removed": effects["route_removed"],
            "reachability_changes": [prefix],
        }

    # ------------------------------------------------------------------ #
    # Lifecycle & logging
    # ------------------------------------------------------------------ #
    def reset(self) -> None:
        self._twin_manager.reset()
        self._mutation_log.clear()

    def get_mutation_log(self) -> list[dict]:
        return [
            {
                "timestamp": rec.timestamp,
                "mutation_type": rec.mutation_type,
                "parameters": rec.parameters,
                "cascading_effects": rec.cascading_effects,
            }
            for rec in self._mutation_log
        ]

    def _finalize(self, mutation_type: str, parameters: dict, effects: dict) -> None:
        self._recompute_service_health()
        self._mutation_log.append(MutationRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            mutation_type=mutation_type,
            parameters=parameters,
            cascading_effects=effects,
        ))

    # ------------------------------------------------------------------ #
    # Service health recomputation (Issue 2)
    # ------------------------------------------------------------------ #
    def _recompute_service_health(self) -> None:
        graph = self.graph
        services = graph.get_services()
        host_ok = {svc["id"]: _host_ok(graph, svc) for svc in services}

        # Initial status purely from host reachability.
        status = {svc["id"]: ("healthy" if host_ok[svc["id"]] else "down")
                  for svc in services}

        # Propagate dependency effects to a fixpoint (host-down always wins).
        for _ in range(len(services) + 1):
            changed = False
            for svc in services:
                svc_id = svc["id"]
                if not host_ok[svc_id]:
                    new = "down"
                else:
                    dep_states = [status[d] for d in graph.get_service_deps(svc_id)]
                    if dep_states and all(s == "down" for s in dep_states):
                        new = "down"
                    elif any(s in ("down", "degraded") for s in dep_states):
                        new = "degraded"
                    else:
                        new = "healthy"
                if new != status[svc_id]:
                    status[svc_id] = new
                    changed = True
            if not changed:
                break

        for svc in services:
            graph.set_node_attr(svc["id"], status=status[svc["id"]])

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _find_peer(node: dict, peer_ip: str):
        bgp = node.get("bgp_state")
        if not bgp:
            return None
        for peer in bgp.get("peers", []):
            if peer.get("peer_ip") == peer_ip:
                return peer
        return None

    @staticmethod
    def _vlan_node_id(site: str, vlan_id: int) -> str:
        prefix = _SITE_PREFIX.get(site, site[:3])
        return f"{prefix}-vlan-{vlan_id}"


def _host_ok(graph: GraphWrapper, svc: dict) -> bool:
    host = svc.get("host_device")
    if not host or not graph.node_exists(host):
        return False
    if graph.get_node(host).get("status") == "down":
        return False
    return not _host_is_isolated(graph, host)
