"""AnalysisEngine — query-only facade over the analysis modules.

Operates on the working twin by default (and the baseline for comparison).
Never mutates graph state. Each method delegates to a specialised module.
"""

from __future__ import annotations

from ..twin.graph_wrapper import GraphWrapper
from ..twin.manager import TwinManager
from . import blast_radius, comparison, path, redundancy, topology


class AnalysisEngine:
    """Pure query engine over the working/baseline twins."""

    def __init__(self, twin_manager: TwinManager):
        self._twin_manager = twin_manager

    @property
    def graph(self) -> GraphWrapper:
        return self._twin_manager.working_wrapper

    @property
    def baseline_graph(self) -> GraphWrapper:
        return self._twin_manager.baseline_wrapper

    # --- Device / link / VLAN inventory ---------------------------------
    def get_device_info(self, device_id: str) -> dict:
        return topology.get_device_info(self.graph, device_id)

    def get_device_interfaces(self, device_id: str) -> dict:
        return topology.get_device_interfaces(self.graph, device_id)

    def get_device_routes(self, device_id: str) -> dict:
        return topology.get_device_routes(self.graph, device_id)

    def get_device_bgp_summary(self, device_id: str):
        return topology.get_device_bgp_summary(self.graph, device_id)

    def get_link_info(self, source: str, target: str) -> dict:
        return topology.get_link_info(self.graph, source, target)

    def get_links(self, scope: str, site: str | None = None) -> dict:
        return topology.get_links(self.graph, scope, site)

    def get_vlan_info(self, vlan_id: int, site: str) -> dict:
        return topology.get_vlan_info(self.graph, vlan_id, site)

    def list_vlans(self, site: str) -> dict:
        return topology.list_vlans(self.graph, site)

    # --- Path / reachability --------------------------------------------
    def trace_route(self, source: str, destination: str) -> dict:
        return path.trace_route(self.graph, source, destination)

    def check_reachability(self, source: str, destination: str) -> dict:
        return path.check_reachability(self.graph, source, destination)

    def get_alternative_paths(self, source: str, destination: str) -> dict:
        return path.get_alternative_paths(self.graph, source, destination)

    # --- Impact ----------------------------------------------------------
    def get_blast_radius(self, component_id: str) -> dict:
        return blast_radius.get_blast_radius(self.graph, component_id)

    def get_service_dependencies(self, service_id: str) -> dict:
        return blast_radius.get_service_dependencies(self.graph, service_id)

    # --- Redundancy ------------------------------------------------------
    def get_redundancy_status(self, component_id: str) -> dict:
        return redundancy.get_redundancy_status(self.graph, component_id)

    def get_single_points_of_failure(self, site: str) -> dict:
        return redundancy.get_single_points_of_failure(self.graph, site)

    def get_failover_path(self, primary_component: str) -> dict:
        return redundancy.get_failover_path(self.graph, primary_component)

    # --- Topology & discovery -------------------------------------------
    def get_site_topology(self, site: str) -> dict:
        return topology.get_site_topology(self.graph, site)

    def get_site_summary(self, site: str) -> dict:
        return topology.get_site_summary(self.graph, site)

    def get_inter_site_connectivity(self, site_a: str, site_b: str) -> dict:
        return topology.get_inter_site_connectivity(self.graph, site_a, site_b)

    def search_devices(self, **filters) -> dict:
        return topology.search_devices(self.graph, **filters)

    # --- State comparison ------------------------------------------------
    def compare_with_baseline(self) -> dict:
        return comparison.compare_with_baseline(self.graph, self.baseline_graph)
