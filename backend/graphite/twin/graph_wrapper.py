"""GraphWrapper — typed accessors over a NetworkX MultiDiGraph.

Downstream layers (analysis, simulation, tools) MUST use this wrapper and never
import NetworkX directly. Read methods return *copies* of node attribute dicts
(with an injected ``id`` key) so callers cannot accidentally mutate graph state;
all mutations go through the explicit mutation helpers.
"""

from __future__ import annotations

from typing import Any, Iterable

import networkx as nx

from ..errors import NodeNotFound


class GraphWrapper:
    """Typed accessor + mutation facade over a NetworkX MultiDiGraph."""

    def __init__(self, graph: nx.MultiDiGraph):
        self._graph = graph

    # ------------------------------------------------------------------ #
    # Node queries
    # ------------------------------------------------------------------ #
    def node_exists(self, node_id: str) -> bool:
        return node_id in self._graph

    def get_node(self, node_id: str) -> dict:
        """Return a copy of a node's attributes with its ``id``.

        Raises:
            NodeNotFound: if the node does not exist.
        """
        if node_id not in self._graph:
            raise NodeNotFound(f"Node '{node_id}' not found")
        return {"id": node_id, **self._graph.nodes[node_id]}

    def get_node_type(self, node_id: str) -> str:
        return self.get_node(node_id).get("node_type")

    def get_nodes_by_type(self, node_type: str, **filters: Any) -> list[dict]:
        """Return all nodes of ``node_type`` whose attributes match ``filters``."""
        results = []
        for node_id, data in self._graph.nodes(data=True):
            if data.get("node_type") != node_type:
                continue
            if all(data.get(k) == v for k, v in filters.items()):
                results.append({"id": node_id, **data})
        return results

    # ------------------------------------------------------------------ #
    # Edge queries
    # ------------------------------------------------------------------ #
    def get_edges(self, source: str, target: str, relation: str | None = None) -> list[dict]:
        """Return edge attribute dicts between two nodes (optionally filtered)."""
        if not self._graph.has_edge(source, target):
            return []
        out = []
        for key, data in self._graph[source][target].items():
            if relation is None or key == relation:
                out.append({"source": source, "target": target, "key": key, **data})
        return out

    def get_neighbors(self, node_id: str, relation: str | None = None,
                      direction: str = "out") -> list[str]:
        """Return neighbour node IDs.

        direction: ``"out"`` (successors), ``"in"`` (predecessors), ``"both"``.
        """
        if node_id not in self._graph:
            raise NodeNotFound(f"Node '{node_id}' not found")
        neighbors: list[str] = []
        if direction in ("out", "both"):
            for _, dst, key in self._graph.out_edges(node_id, keys=True):
                if relation is None or key == relation:
                    neighbors.append(dst)
        if direction in ("in", "both"):
            for src, _, key in self._graph.in_edges(node_id, keys=True):
                if relation is None or key == relation:
                    neighbors.append(src)
        # Preserve order, drop duplicates.
        seen: set[str] = set()
        unique = []
        for n in neighbors:
            if n not in seen:
                seen.add(n)
                unique.append(n)
        return unique

    def get_edges_by_relation(self, relation: str) -> list[tuple[str, str, dict]]:
        return [
            (src, dst, data)
            for src, dst, key, data in self._graph.edges(keys=True, data=True)
            if key == relation
        ]

    # ------------------------------------------------------------------ #
    # Typed convenience methods
    # ------------------------------------------------------------------ #
    def get_sites(self) -> list[dict]:
        return self.get_nodes_by_type("site")

    def get_devices(self, site: str | None = None, device_type: str | None = None,
                    status: str | None = None) -> list[dict]:
        filters: dict[str, Any] = {}
        if site is not None:
            filters["site"] = site
        if device_type is not None:
            filters["device_type"] = device_type
        if status is not None:
            filters["status"] = status
        return self.get_nodes_by_type("device", **filters)

    def get_vlans(self, site: str | None = None) -> list[dict]:
        filters = {"site": site} if site is not None else {}
        return self.get_nodes_by_type("vlan", **filters)

    def get_services(self, site: str | None = None) -> list[dict]:
        filters = {"site": site} if site is not None else {}
        return self.get_nodes_by_type("service", **filters)

    def get_user_groups(self, site: str | None = None) -> list[dict]:
        filters = {"site": site} if site is not None else {}
        return self.get_nodes_by_type("user_group", **filters)

    def get_endpoint_groups(self, site: str | None = None) -> list[dict]:
        filters = {"site": site} if site is not None else {}
        return self.get_nodes_by_type("endpoint_group", **filters)

    def get_zones_served_by(self, device_id: str) -> list[dict]:
        """Return endpoint_group nodes directly served by a device (serves_zone edges)."""
        groups = []
        for edge in self.get_edges_out(device_id, "serves_zone"):
            target = edge["target"]
            if self.node_exists(target) and self.get_node_type(target) == "endpoint_group":
                groups.append(self.get_node(target))
        return groups

    # ------------------------------------------------------------------ #
    # Domain-specific helpers
    # ------------------------------------------------------------------ #
    def get_physical_links(self, device_id: str, only_up: bool = False) -> list[dict]:
        """Return outgoing physical_link edges for a device."""
        links = self.get_edges_out(device_id, "physical_link")
        if only_up:
            links = [e for e in links if e.get("status") == "up"]
        return links

    def get_edges_out(self, node_id: str, relation: str | None = None) -> list[dict]:
        if node_id not in self._graph:
            raise NodeNotFound(f"Node '{node_id}' not found")
        out = []
        for _, dst, key, data in self._graph.out_edges(node_id, keys=True, data=True):
            if relation is None or key == relation:
                out.append({"source": node_id, "target": dst, "key": key, **data})
        return out

    def get_physical_neighbors(self, device_id: str, only_up: bool = False) -> list[str]:
        return [e["target"] for e in self.get_physical_links(device_id, only_up=only_up)]

    def get_vlan_devices(self, vlan_node_id: str) -> list[str]:
        """Devices that carry this VLAN (carries_vlan predecessors)."""
        return self.get_neighbors(vlan_node_id, relation="carries_vlan", direction="in")

    def get_vlan_user_groups(self, vlan_node_id: str) -> list[dict]:
        ids = self.get_neighbors(vlan_node_id, relation="serves", direction="out")
        return [self.get_node(i) for i in ids]

    def get_service_deps(self, service_id: str) -> list[str]:
        return self.get_neighbors(service_id, relation="depends_on", direction="out")

    def get_service_dependents(self, service_id: str) -> list[str]:
        return self.get_neighbors(service_id, relation="depends_on", direction="in")

    def get_service_host(self, service_id: str) -> str | None:
        hosts = self.get_neighbors(service_id, relation="hosted_on", direction="out")
        return hosts[0] if hosts else None

    def find_link_edge(self, source: str, target: str) -> dict | None:
        """Return the physical_link edge data for source->target, or None."""
        edges = self.get_edges(source, target, relation="physical_link")
        return edges[0] if edges else None

    def find_edge_by_link_id(self, link_id: str) -> tuple[str, str, dict] | None:
        """Locate a physical_link edge by its ``link_id`` attribute."""
        for src, dst, data in self.get_edges_by_relation("physical_link"):
            if data.get("link_id") == link_id:
                return (src, dst, data)
        return None

    # ------------------------------------------------------------------ #
    # Mutation helpers (used by the simulation engine)
    # ------------------------------------------------------------------ #
    def set_node_attr(self, node_id: str, **attrs: Any) -> None:
        if node_id not in self._graph:
            raise NodeNotFound(f"Node '{node_id}' not found")
        self._graph.nodes[node_id].update(attrs)

    def set_edge_attr(self, source: str, target: str, relation: str, **attrs: Any) -> None:
        if not self._graph.has_edge(source, target, key=relation):
            raise NodeNotFound(f"Edge ({source}->{target}, {relation}) not found")
        self._graph[source][target][relation].update(attrs)

    def add_node(self, node_id: str, **attrs: Any) -> None:
        self._graph.add_node(node_id, **attrs)

    def remove_node(self, node_id: str) -> None:
        if node_id in self._graph:
            self._graph.remove_node(node_id)

    def add_edge(self, source: str, target: str, relation: str, **attrs: Any) -> None:
        self._graph.add_edge(source, target, key=relation, relation=relation, **attrs)

    def remove_edge(self, source: str, target: str, relation: str) -> None:
        if self._graph.has_edge(source, target, key=relation):
            self._graph.remove_edge(source, target, key=relation)

    def has_edge(self, source: str, target: str, relation: str | None = None) -> bool:
        if relation is None:
            return self._graph.has_edge(source, target)
        return self._graph.has_edge(source, target, key=relation)

    # ------------------------------------------------------------------ #
    # Raw access
    # ------------------------------------------------------------------ #
    @property
    def nx_graph(self) -> nx.MultiDiGraph:
        """Direct access to the underlying NetworkX graph (use sparingly)."""
        return self._graph

    def all_nodes(self) -> Iterable[str]:
        return self._graph.nodes()
