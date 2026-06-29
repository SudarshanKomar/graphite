"""MCP resource definitions — browsable read-only topology state.

Three curated resources for external agents that want to inspect the digital
twin state without calling tools:

* ``graphite://topology/overview`` — global network health and WAN links
* ``graphite://topology/sites/{site}`` — per-site device/VLAN/service inventory
* ``graphite://state/diff`` — current mutations vs healthy baseline
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class ResourceDef:
    """An MCP resource definition."""

    uri: str
    name: str
    description: str


# Static resource definitions (per-site resources are generated dynamically).
STATIC_RESOURCES = [
    ResourceDef(
        "graphite://topology/overview",
        "Network Overview",
        "Global topology: all sites with health status, device counts, and "
        "inter-site WAN links.",
    ),
    ResourceDef(
        "graphite://state/diff",
        "Current Mutations",
        "Changes applied to the working twin versus the healthy baseline. "
        "Empty when no mutations are active.",
    ),
]

# Site short names for dynamic resource generation.
_SITES = ("bangalore", "london", "newyork", "singapore")


def list_all_resources() -> list[ResourceDef]:
    """Return the full resource catalogue including per-site resources."""
    resources = list(STATIC_RESOURCES)
    for site in _SITES:
        resources.append(ResourceDef(
            f"graphite://topology/sites/{site}",
            f"Site Topology: {site}",
            f"Full topology of the {site} site — devices, links, VLANs, "
            f"services, and user groups.",
        ))
    return resources


def read_resource(uri: str, analysis_engine) -> str:
    """Read a resource by URI, returning JSON text.

    Raises ``ValueError`` for unknown URIs.
    """
    if uri == "graphite://topology/overview":
        sites = []
        for short in _SITES:
            try:
                summary = analysis_engine.get_site_summary(short)
                sites.append(summary)
            except Exception:
                pass  # site may not exist in a test dataset
        return json.dumps({"sites": sites}, default=str)

    if uri == "graphite://state/diff":
        return json.dumps(analysis_engine.compare_with_baseline(), default=str)

    if uri.startswith("graphite://topology/sites/"):
        site = uri.rsplit("/", 1)[-1]
        return json.dumps(analysis_engine.get_site_topology(site), default=str)

    raise ValueError(f"Unknown resource URI: {uri}")
