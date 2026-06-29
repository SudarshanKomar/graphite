"""TwinBuilder — constructs a NetworkX MultiDiGraph from JSON source files.

This is a twin-layer constructor and therefore (together with
:mod:`graphite.twin.graph_wrapper`) is permitted to touch NetworkX directly.
All *downstream* code (analysis, simulation, tools) goes through GraphWrapper.

Field mapping applied during construction (per spec C7/builder defaults):
  - devices.json ``type``  -> node ``device_type``
  - services.json ``type`` -> node ``service_type``
  - VLANs get ``status="active"`` (not present in JSON)
  - bgp_peers.json entries are merged into the matching device node ``bgp_state``
  - telemetry_snapshot.json entries merged into device node ``telemetry``
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from ..errors import ValidationError
from .validator import Validator


class TwinBuilder:
    """Builds a NetworkX graph from JSON source-of-truth files."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"network_state directory not found: {self.data_dir}")

        # Raw JSON payloads, populated by _load_json_files().
        self._sites: list[dict] = []
        self._devices: list[dict] = []
        self._links: list[dict] = []
        self._vlans: list[dict] = []
        self._bgp: list[dict] = []
        self._services: list[dict] = []
        self._user_groups: list[dict] = []
        self._endpoint_groups: list[dict] = []
        self._telemetry: dict = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def build(self) -> nx.MultiDiGraph:
        """Load all JSON files, validate, and construct the complete graph."""
        self._load_json_files()
        self._validate_source_data()

        graph = nx.MultiDiGraph()
        self._load_sites(graph)
        self._load_devices(graph)
        self._load_bgp_peers(graph)
        self._load_telemetry(graph)
        self._load_links(graph)
        self._load_vlans(graph)
        self._load_services(graph)
        self._load_user_groups(graph)
        self._load_endpoint_groups(graph)

        self._validate_graph(graph)
        return graph

    # ------------------------------------------------------------------ #
    # JSON loading
    # ------------------------------------------------------------------ #
    def _read(self, name: str) -> object:
        path = self.data_dir / name
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _load_json_files(self) -> None:
        sites_dir = self.data_dir / "sites"
        self._sites = [
            json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(sites_dir.glob("*.json"))
        ]
        self._devices = self._read("devices.json")
        self._links = self._read("links.json")
        self._vlans = self._read("vlans.json")
        self._bgp = self._read("bgp_peers.json")
        self._services = self._read("services.json")
        self._user_groups = self._read("user_groups.json")
        ep_path = self.data_dir / "endpoint_groups.json"
        self._endpoint_groups = json.loads(ep_path.read_text(encoding="utf-8")) if ep_path.exists() else []
        self._telemetry = self._read("telemetry_snapshot.json")

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def _validate_source_data(self) -> None:
        device_ids = {d["id"] for d in self._devices}
        site_names = {s["short_name"] for s in self._sites}
        vlan_keys = {(v["vlan_id"], v["site"]) for v in self._vlans}

        errors: list[str] = []
        errors += Validator.validate_sites(self._sites)
        errors += Validator.validate_devices(self._devices)
        errors += Validator.validate_links(self._links, device_ids)
        errors += Validator.validate_vlans(self._vlans, device_ids, site_names)
        errors += Validator.validate_bgp_peers(self._bgp, device_ids)
        errors += Validator.validate_services(self._services, device_ids)
        errors += Validator.validate_user_groups(self._user_groups, vlan_keys)
        errors += Validator.validate_global_unique_ids(
            [s["id"] for s in self._sites],
            [d["id"] for d in self._devices],
            [link["id"] for link in self._links],
            [s["id"] for s in self._services],
            [g["id"] for g in self._user_groups],
        )
        errors += Validator.validate_interface_references(self._devices, device_ids)

        if errors:
            raise ValidationError(errors)

    def _validate_graph(self, graph: nx.MultiDiGraph) -> None:
        """Cheap post-construction invariant checks (schema invariants 1-2)."""
        errors: list[str] = []
        for node, data in graph.nodes(data=True):
            if "node_type" not in data:
                errors.append(f"node '{node}' missing node_type")
        for src, dst, key, data in graph.edges(keys=True, data=True):
            if data.get("relation") != key:
                errors.append(
                    f"edge ({src}->{dst}, key={key}) relation attr mismatch: "
                    f"{data.get('relation')!r}"
                )
        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------ #
    # Node loaders
    # ------------------------------------------------------------------ #
    def _load_sites(self, graph: nx.MultiDiGraph) -> None:
        for site in self._sites:
            graph.add_node(
                site["id"],
                node_type="site",
                name=site["name"],
                short_name=site["short_name"],
                location=site.get("location", {}),
                as_number=site["as_number"],
                prefix_block=site["prefix_block"],
                employee_count=site["employee_count"],
                description=site.get("description"),
            )

    def _load_devices(self, graph: nx.MultiDiGraph) -> None:
        for dev in self._devices:
            graph.add_node(
                dev["id"],
                node_type="device",
                name=dev["name"],
                device_type=dev["type"],          # field rename: type -> device_type
                vendor=dev["vendor"],
                model=dev.get("model"),
                os=dev["os"],
                site=dev["site"],
                status=dev["status"],
                management_ip=dev.get("management_ip"),
                role=dev.get("role"),
                interfaces=dev.get("interfaces", []),
                routes=dev.get("routes", []),
                bgp_state=None,     # populated by _load_bgp_peers
                telemetry=None,     # populated by _load_telemetry
            )
            # device -> site membership
            graph.add_edge(dev["id"], f"site-{dev['site']}", key="belongs_to",
                           relation="belongs_to")

    def _load_bgp_peers(self, graph: nx.MultiDiGraph) -> None:
        for entry in self._bgp:
            device_id = entry["device"]
            if device_id not in graph:
                continue
            graph.nodes[device_id]["bgp_state"] = {
                "local_as": entry["local_as"],
                "router_id": entry["router_id"],
                "peers": [dict(peer) for peer in entry.get("peers", [])],
            }

    def _load_telemetry(self, graph: nx.MultiDiGraph) -> None:
        devices = self._telemetry.get("devices", {})
        for device_id, snapshot in devices.items():
            if device_id in graph:
                graph.nodes[device_id]["telemetry"] = snapshot

    def _load_vlans(self, graph: nx.MultiDiGraph) -> None:
        for vlan in self._vlans:
            node_id = self._vlan_node_id(vlan["site"], vlan["vlan_id"])
            graph.add_node(
                node_id,
                node_type="vlan",
                vlan_id=vlan["vlan_id"],
                name=vlan["name"],
                subnet=vlan["subnet"],
                gateway=vlan["gateway"],
                site=vlan["site"],
                status="active",   # builder default (not in JSON)
                description=vlan.get("description"),
            )
            graph.add_edge(node_id, f"site-{vlan['site']}", key="belongs_to",
                           relation="belongs_to")
            for device_id in vlan.get("devices", []):
                graph.add_edge(device_id, node_id, key="carries_vlan",
                               relation="carries_vlan", tagged=True)

    def _load_services(self, graph: nx.MultiDiGraph) -> None:
        for svc in self._services:
            graph.add_node(
                svc["id"],
                node_type="service",
                name=svc["name"],
                service_type=svc["type"],         # field rename: type -> service_type
                site=svc["site"],
                host_device=svc["host_device"],
                port=svc.get("port"),
                protocol=svc.get("protocol"),
                status=svc["status"],
                criticality=svc["criticality"],
                description=svc.get("description"),
            )
            graph.add_edge(svc["id"], f"site-{svc['site']}", key="belongs_to",
                           relation="belongs_to")
            graph.add_edge(svc["id"], svc["host_device"], key="hosted_on",
                           relation="hosted_on")
            for dep in svc.get("depends_on", []):
                graph.add_edge(svc["id"], dep, key="depends_on", relation="depends_on")

    def _load_user_groups(self, graph: nx.MultiDiGraph) -> None:
        for grp in self._user_groups:
            graph.add_node(
                grp["id"],
                node_type="user_group",
                name=grp["name"],
                site=grp["site"],
                vlan_id=grp["vlan_id"],
                estimated_users=grp["estimated_users"],
                device_types=grp.get("device_types", []),
                description=grp.get("description"),
            )
            graph.add_edge(grp["id"], f"site-{grp['site']}", key="belongs_to",
                           relation="belongs_to")
            vlan_node = self._vlan_node_id(grp["site"], grp["vlan_id"])
            if vlan_node in graph:
                graph.add_edge(vlan_node, grp["id"], key="serves", relation="serves")

    def _load_endpoint_groups(self, graph: nx.MultiDiGraph) -> None:
        """V2.1.1: locality-aware endpoint groups with device breakdowns."""
        for eg in self._endpoint_groups:
            graph.add_node(
                eg["id"],
                node_type="endpoint_group",
                name=eg["name"],
                site=eg["site"],
                zone=eg.get("zone"),
                vlan_id=eg["vlan_id"],
                estimated_users=eg["estimated_users"],
                device_breakdown=eg.get("device_breakdown", {}),
                access_device=eg.get("access_device"),
                description=eg.get("description"),
            )
            graph.add_edge(eg["id"], f"site-{eg['site']}", key="belongs_to",
                           relation="belongs_to")
            if eg.get("access_device") and eg["access_device"] in graph:
                graph.add_edge(eg["access_device"], eg["id"],
                               key="serves_zone", relation="serves_zone")

        # V2.1.1 invariant: per-site endpoint-group user total must equal
        # user-group user total.
        self._validate_endpoint_group_parity()

    def _load_links(self, graph: nx.MultiDiGraph) -> None:
        for link in self._links:
            attrs = {
                "relation": "physical_link",
                "link_id": link["id"],
                "bandwidth": link["bandwidth"],
                "latency_ms": link["latency_ms"],
                "link_type": link["link_type"],
                "status": link["status"],
                "source_interface": link.get("source_interface"),
                "target_interface": link.get("target_interface"),
            }
            # Bidirectional pair (schema invariant 3).
            graph.add_edge(link["source"], link["target"], key="physical_link", **attrs)
            graph.add_edge(link["target"], link["source"], key="physical_link", **attrs)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _validate_endpoint_group_parity(self) -> None:
        """Ensure per-site endpoint-group users == user-group users.

        Only validates sites that have at least one endpoint group. Sites with
        no endpoint groups (e.g. Singapore DC) are skipped.
        """
        if not self._endpoint_groups:
            return
        from collections import defaultdict
        eg_by_site: dict[str, int] = defaultdict(int)
        for eg in self._endpoint_groups:
            eg_by_site[eg["site"]] += eg["estimated_users"]

        ug_by_site: dict[str, int] = defaultdict(int)
        for ug in self._user_groups:
            ug_by_site[ug["site"]] += ug["estimated_users"]

        errors: list[str] = []
        for site, eg_total in eg_by_site.items():
            ug_total = ug_by_site.get(site, 0)
            if eg_total != ug_total:
                errors.append(
                    f"Endpoint-group user parity mismatch for site '{site}': "
                    f"endpoint_groups={eg_total}, user_groups={ug_total}"
                )
        if errors:
            raise ValidationError(errors)

    @staticmethod
    def _vlan_node_id(site: str, vlan_id: int) -> str:
        prefix = _SITE_PREFIX.get(site, site[:3])
        return f"{prefix}-vlan-{vlan_id}"


# Short site prefixes used in node IDs (matches device ID convention).
_SITE_PREFIX = {
    "bangalore": "blr",
    "london": "lon",
    "newyork": "nyc",
    "singapore": "sg",
}
