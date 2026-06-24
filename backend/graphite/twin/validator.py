"""Validation of JSON source-of-truth data prior to graph construction.

Implements the validation rules from
``specs/schemas/baseline-twin-json-schema.md`` (rules 1-9). Each ``validate_*``
method returns a list of human-readable error strings (empty list == valid) so
that the builder can aggregate and report every problem at once rather than
failing on the first issue.
"""

from __future__ import annotations

from typing import Any

DEVICE_TYPES = {
    "router",
    "core_switch",
    "distribution_switch",
    "access_switch",
    "leaf_switch",
    "spine_switch",
    "firewall",
    "load_balancer",
    "server",
    "access_point",
}

LINK_TYPES = {"campus", "datacenter", "wan", "mpls", "vpn"}
STATUS_UP_DOWN = {"up", "down"}
ROUTE_PROTOCOLS = {"static", "connected", "bgp", "ospf"}
BGP_STATES = {"established", "idle", "active"}
SERVICE_STATUSES = {"healthy", "degraded", "down"}
CRITICALITIES = {"critical", "high", "medium", "low"}


def _require(obj: dict, fields: tuple[str, ...], label: str, errors: list[str]) -> None:
    for field in fields:
        if field not in obj or obj[field] in (None, ""):
            errors.append(f"{label}: missing required field '{field}'")


class Validator:
    """Stateless validation helpers for each entity type."""

    @staticmethod
    def validate_sites(sites: list[dict]) -> list[str]:
        errors: list[str] = []
        for site in sites:
            label = f"site '{site.get('short_name', site.get('id', '?'))}'"
            _require(site, ("id", "name", "short_name", "as_number", "prefix_block",
                            "employee_count"), label, errors)
            loc = site.get("location") or {}
            if not loc.get("city") or not loc.get("country"):
                errors.append(f"{label}: location.city and location.country are required")
        return errors

    @staticmethod
    def validate_devices(devices: list[dict]) -> list[str]:
        errors: list[str] = []
        for dev in devices:
            label = f"device '{dev.get('id', '?')}'"
            _require(dev, ("id", "name", "type", "vendor", "os", "site", "status"),
                     label, errors)
            if dev.get("type") and dev["type"] not in DEVICE_TYPES:
                errors.append(f"{label}: invalid type '{dev['type']}'")
            if dev.get("status") and dev["status"] not in STATUS_UP_DOWN:
                errors.append(f"{label}: invalid status '{dev['status']}'")
            if not isinstance(dev.get("interfaces"), list):
                errors.append(f"{label}: 'interfaces' must be a list")
            if not isinstance(dev.get("routes"), list):
                errors.append(f"{label}: 'routes' must be a list")
            for route in dev.get("routes", []):
                if route.get("protocol") and route["protocol"] not in ROUTE_PROTOCOLS:
                    errors.append(f"{label}: invalid route protocol '{route['protocol']}'")
        return errors

    @staticmethod
    def validate_links(links: list[dict], device_ids: set[str]) -> list[str]:
        errors: list[str] = []
        for link in links:
            label = f"link '{link.get('id', '?')}'"
            _require(link, ("id", "source", "target", "bandwidth", "latency_ms",
                            "link_type", "status"), label, errors)
            if link.get("source") and link["source"] not in device_ids:
                errors.append(f"{label}: source device '{link['source']}' does not exist")
            if link.get("target") and link["target"] not in device_ids:
                errors.append(f"{label}: target device '{link['target']}' does not exist")
            if link.get("link_type") and link["link_type"] not in LINK_TYPES:
                errors.append(f"{label}: invalid link_type '{link['link_type']}'")
        return errors

    @staticmethod
    def validate_vlans(vlans: list[dict], device_ids: set[str],
                       site_names: set[str]) -> list[str]:
        errors: list[str] = []
        seen: set[tuple[int, str]] = set()
        for vlan in vlans:
            label = f"vlan {vlan.get('vlan_id', '?')}@{vlan.get('site', '?')}"
            _require(vlan, ("vlan_id", "name", "subnet", "gateway", "site"), label, errors)
            key = (vlan.get("vlan_id"), vlan.get("site"))
            if key in seen:
                errors.append(f"{label}: duplicate (vlan_id, site) pair")
            seen.add(key)
            if vlan.get("site") and vlan["site"] not in site_names:
                errors.append(f"{label}: unknown site '{vlan['site']}'")
            for dev in vlan.get("devices", []):
                if dev not in device_ids:
                    errors.append(f"{label}: references unknown device '{dev}'")
        return errors

    @staticmethod
    def validate_bgp_peers(bgp_entries: list[dict], device_ids: set[str]) -> list[str]:
        errors: list[str] = []
        # Build a set of (device, peer_device) for reciprocity checking.
        sessions: set[tuple[str, str]] = set()
        for entry in bgp_entries:
            label = f"bgp '{entry.get('device', '?')}'"
            _require(entry, ("device", "local_as", "router_id", "peers"), label, errors)
            if entry.get("device") and entry["device"] not in device_ids:
                errors.append(f"{label}: device does not exist")
            for peer in entry.get("peers", []):
                _require(peer, ("peer_ip", "peer_device", "peer_as", "state"),
                         f"{label} peer", errors)
                if peer.get("state") and peer["state"] not in BGP_STATES:
                    errors.append(f"{label}: invalid peer state '{peer['state']}'")
                if peer.get("peer_device") and peer["peer_device"] not in device_ids:
                    errors.append(f"{label}: peer_device '{peer['peer_device']}' does not exist")
                if entry.get("device") and peer.get("peer_device"):
                    sessions.add((entry["device"], peer["peer_device"]))
        # Reciprocity (rule 6): every A->B session needs a B->A entry.
        for src, dst in sessions:
            if (dst, src) not in sessions:
                errors.append(
                    f"bgp: non-reciprocal session — '{src}' peers with '{dst}' "
                    f"but '{dst}' has no peering entry back to '{src}'"
                )
        return errors

    @staticmethod
    def validate_services(services: list[dict], device_ids: set[str]) -> list[str]:
        errors: list[str] = []
        service_ids = {s.get("id") for s in services}
        for svc in services:
            label = f"service '{svc.get('id', '?')}'"
            _require(svc, ("id", "name", "type", "site", "host_device", "status",
                           "criticality"), label, errors)
            if svc.get("host_device") and svc["host_device"] not in device_ids:
                errors.append(f"{label}: host_device '{svc['host_device']}' does not exist")
            if svc.get("status") and svc["status"] not in SERVICE_STATUSES:
                errors.append(f"{label}: invalid status '{svc['status']}'")
            if svc.get("criticality") and svc["criticality"] not in CRITICALITIES:
                errors.append(f"{label}: invalid criticality '{svc['criticality']}'")
            for dep in svc.get("depends_on", []):
                if dep not in service_ids:
                    errors.append(f"{label}: depends_on unknown service '{dep}'")
        return errors

    @staticmethod
    def validate_user_groups(groups: list[dict], vlan_keys: set[tuple[int, str]]) -> list[str]:
        errors: list[str] = []
        for grp in groups:
            label = f"user_group '{grp.get('id', '?')}'"
            _require(grp, ("id", "name", "site", "vlan_id", "estimated_users"), label, errors)
            key = (grp.get("vlan_id"), grp.get("site"))
            if grp.get("vlan_id") is not None and key not in vlan_keys:
                errors.append(
                    f"{label}: vlan_id {grp.get('vlan_id')} not found at site "
                    f"'{grp.get('site')}'"
                )
        return errors

    @staticmethod
    def validate_global_unique_ids(*id_lists: list[str]) -> list[str]:
        """Rule 8: all IDs across entity types must be globally unique."""
        errors: list[str] = []
        seen: set[str] = set()
        for ids in id_lists:
            for _id in ids:
                if _id in seen:
                    errors.append(f"duplicate global ID '{_id}'")
                seen.add(_id)
        return errors

    @staticmethod
    def validate_interface_references(devices: list[dict], device_ids: set[str]) -> list[str]:
        """Rule 9: interface connected_to references must point to valid devices."""
        errors: list[str] = []
        for dev in devices:
            for iface in dev.get("interfaces", []):
                target = iface.get("connected_to")
                if target is not None and target not in device_ids:
                    errors.append(
                        f"device '{dev.get('id')}' interface "
                        f"'{iface.get('name')}': connected_to '{target}' does not exist"
                    )
        return errors
