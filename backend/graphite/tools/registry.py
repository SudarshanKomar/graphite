"""Default tool registry — wires all 34 tools to the engines.

Tools are thin delegations to ``AnalysisEngine`` (query) or ``SimulationEngine``
(mutation). Each carries a JSON-Schema parameter spec for the LLM. Only query
tools are surfaced to the agent (see ``ToolRegistry.list_agent_tools``).

Note (deviation D5): for Run 1 the tool table lives here rather than split across
``device_tools.py``, ``link_tools.py``, … as in folder-structure.md. The split is
a cosmetic Run 2 refactor; the registry contract is unchanged.
"""

from __future__ import annotations

from .base import ToolContext, ToolRegistry, ToolSchema


def _obj(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
    }


_STR = {"type": "string"}
_INT = {"type": "integer"}
_NUM = {"type": "number"}


def _spec(name, category, description, properties, required, returns):
    return ToolSchema(
        name=name, description=description,
        parameters=_obj(properties, required), returns=returns, category=category,
    )


def build_default_registry(context: ToolContext) -> ToolRegistry:
    reg = ToolRegistry(context)

    def q(ctx):
        return ctx.analysis_engine

    def m(ctx):
        return ctx.simulation_engine

    # ----- Device (query) ---------------------------------------------- #
    reg.register(_spec("get_device_info", "query", "Device metadata and status.",
                       {"device_id": _STR}, ["device_id"], "device object"),
                 lambda c, device_id: q(c).get_device_info(device_id))
    reg.register(_spec("get_device_interfaces", "query", "Interfaces with IPs/VLANs.",
                       {"device_id": _STR}, ["device_id"], "interfaces list"),
                 lambda c, device_id: q(c).get_device_interfaces(device_id))
    reg.register(_spec("get_device_routes", "query", "Routing table for a device.",
                       {"device_id": _STR}, ["device_id"], "routes list"),
                 lambda c, device_id: q(c).get_device_routes(device_id))
    reg.register(_spec("get_device_bgp_summary", "query", "BGP peers/state/prefixes.",
                       {"device_id": _STR}, ["device_id"], "bgp summary or null"),
                 lambda c, device_id: q(c).get_device_bgp_summary(device_id))

    # ----- Link (query) ------------------------------------------------ #
    reg.register(_spec("get_link_info", "query", "Details for a link between two devices.",
                       {"source": _STR, "target": _STR}, ["source", "target"], "link object"),
                 lambda c, source, target: q(c).get_link_info(source, target))
    reg.register(_spec("get_links", "query", "List links by scope (site|wan|all).",
                       {"scope": _STR, "site": _STR}, ["scope"], "links list"),
                 lambda c, scope, site=None: q(c).get_links(scope, site))

    # ----- VLAN (query) ------------------------------------------------ #
    reg.register(_spec("get_vlan_info", "query", "VLAN details, devices, user count.",
                       {"vlan_id": _INT, "site": _STR}, ["vlan_id", "site"], "vlan object"),
                 lambda c, vlan_id, site: q(c).get_vlan_info(vlan_id, site))
    reg.register(_spec("list_vlans", "query", "All VLANs at a site.",
                       {"site": _STR}, ["site"], "vlans list"),
                 lambda c, site: q(c).list_vlans(site))

    # ----- Routing & path (query) -------------------------------------- #
    reg.register(_spec("trace_route", "query", "Hop-by-hop path with latency.",
                       {"source": _STR, "destination": _STR}, ["source", "destination"],
                       "trace object"),
                 lambda c, source, destination: q(c).trace_route(source, destination))
    reg.register(_spec("check_reachability", "query", "Boolean reachability + path.",
                       {"source": _STR, "destination": _STR}, ["source", "destination"],
                       "reachability object"),
                 lambda c, source, destination: q(c).check_reachability(source, destination))
    reg.register(_spec("get_alternative_paths", "query", "All paths (ECMP/backup).",
                       {"source": _STR, "destination": _STR}, ["source", "destination"],
                       "paths object"),
                 lambda c, source, destination: q(c).get_alternative_paths(source, destination))

    # ----- Impact (query) ---------------------------------------------- #
    reg.register(_spec("get_blast_radius", "query",
                       "Full impact of a failed component (device/VLAN/service/link id).",
                       {"component_id": _STR}, ["component_id"], "blast radius object"),
                 lambda c, component_id: q(c).get_blast_radius(component_id))
    reg.register(_spec("get_service_dependencies", "query", "Service dependency graph.",
                       {"service_id": _STR}, ["service_id"], "dependency object"),
                 lambda c, service_id: q(c).get_service_dependencies(service_id))

    # ----- Redundancy (query) ------------------------------------------ #
    reg.register(_spec("get_redundancy_status", "query", "Redundancy/failover for a component.",
                       {"component_id": _STR}, ["component_id"], "redundancy object"),
                 lambda c, component_id: q(c).get_redundancy_status(component_id))
    reg.register(_spec("get_single_points_of_failure", "query", "SPOFs for a site.",
                       {"site": _STR}, ["site"], "spof object"),
                 lambda c, site: q(c).get_single_points_of_failure(site))
    reg.register(_spec("get_failover_path", "query", "Failover path for a component.",
                       {"primary_component": _STR}, ["primary_component"], "failover object"),
                 lambda c, primary_component: q(c).get_failover_path(primary_component))

    # ----- Topology & discovery (query) -------------------------------- #
    reg.register(_spec("get_site_topology", "query", "Full topology of a site.",
                       {"site": _STR}, ["site"], "topology object"),
                 lambda c, site: q(c).get_site_topology(site))
    reg.register(_spec("get_site_summary", "query", "High-level site stats + health.",
                       {"site": _STR}, ["site"], "summary object"),
                 lambda c, site: q(c).get_site_summary(site))
    reg.register(_spec("get_inter_site_connectivity", "query", "WAN+BGP between two sites.",
                       {"site_a": _STR, "site_b": _STR}, ["site_a", "site_b"], "connectivity object"),
                 lambda c, site_a, site_b: q(c).get_inter_site_connectivity(site_a, site_b))
    reg.register(_spec("search_devices", "query", "Search devices by filters.",
                       {"query": _STR, "device_type": _STR, "site": _STR,
                        "status": _STR, "vendor": _STR}, [], "results object"),
                 lambda c, **kw: q(c).search_devices(**kw))

    # ----- State (query) ----------------------------------------------- #
    reg.register(_spec("compare_with_baseline", "query", "Diff working twin vs baseline.",
                       {}, [], "diff object"),
                 lambda c: q(c).compare_with_baseline())

    # ===== Mutation tools (API only) =================================== #
    reg.register(_spec("disable_device", "mutation", "Mark device down + cascade.",
                       {"device_id": _STR}, ["device_id"], "result object"),
                 lambda c, device_id: m(c).disable_device(device_id))
    reg.register(_spec("enable_device", "mutation", "Mark device up + restore.",
                       {"device_id": _STR}, ["device_id"], "result object"),
                 lambda c, device_id: m(c).enable_device(device_id))
    reg.register(_spec("disable_link", "mutation", "Mark link down + cascade.",
                       {"source": _STR, "target": _STR}, ["source", "target"], "result object"),
                 lambda c, source, target: m(c).disable_link(source, target))
    reg.register(_spec("enable_link", "mutation", "Mark link up + restore.",
                       {"source": _STR, "target": _STR}, ["source", "target"], "result object"),
                 lambda c, source, target: m(c).enable_link(source, target))
    reg.register(_spec("set_link_latency", "mutation", "Change link latency.",
                       {"source": _STR, "target": _STR, "latency_ms": _NUM},
                       ["source", "target", "latency_ms"], "result object"),
                 lambda c, source, target, latency_ms:
                     m(c).set_link_latency(source, target, latency_ms))
    reg.register(_spec("add_vlan", "mutation", "Add a VLAN to a site.",
                       {"vlan_id": _INT, "site": _STR, "subnet": _STR, "name": _STR,
                        "devices": {"type": "array", "items": _STR}},
                       ["vlan_id", "site", "subnet", "name", "devices"], "result object"),
                 lambda c, vlan_id, site, subnet, name, devices:
                     m(c).add_vlan(vlan_id, site, subnet, name, devices))
    reg.register(_spec("remove_vlan", "mutation", "Remove a VLAN from a site + cascade.",
                       {"vlan_id": _INT, "site": _STR}, ["vlan_id", "site"], "result object"),
                 lambda c, vlan_id, site: m(c).remove_vlan(vlan_id, site))
    reg.register(_spec("add_static_route", "mutation", "Add a static route.",
                       {"device_id": _STR, "prefix": _STR, "next_hop": _STR},
                       ["device_id", "prefix", "next_hop"], "result object"),
                 lambda c, device_id, prefix, next_hop:
                     m(c).add_static_route(device_id, prefix, next_hop))
    reg.register(_spec("remove_static_route", "mutation", "Remove a static route.",
                       {"device_id": _STR, "prefix": _STR}, ["device_id", "prefix"],
                       "result object"),
                 lambda c, device_id, prefix: m(c).remove_static_route(device_id, prefix))
    reg.register(_spec("disable_bgp_peer", "mutation", "Disable BGP peer (reciprocal).",
                       {"device_id": _STR, "peer_ip": _STR}, ["device_id", "peer_ip"],
                       "result object"),
                 lambda c, device_id, peer_ip: m(c).disable_bgp_peer(device_id, peer_ip))
    reg.register(_spec("enable_bgp_peer", "mutation", "Enable BGP peer (reciprocal).",
                       {"device_id": _STR, "peer_ip": _STR}, ["device_id", "peer_ip"],
                       "result object"),
                 lambda c, device_id, peer_ip: m(c).enable_bgp_peer(device_id, peer_ip))
    reg.register(_spec("withdraw_prefix", "mutation", "Withdraw a BGP prefix.",
                       {"device_id": _STR, "prefix": _STR}, ["device_id", "prefix"],
                       "result object"),
                 lambda c, device_id, prefix: m(c).withdraw_prefix(device_id, prefix))
    reg.register(_spec("advertise_prefix", "mutation", "Advertise a BGP prefix.",
                       {"device_id": _STR, "prefix": _STR}, ["device_id", "prefix"],
                       "result object"),
                 lambda c, device_id, prefix: m(c).advertise_prefix(device_id, prefix))

    return reg
