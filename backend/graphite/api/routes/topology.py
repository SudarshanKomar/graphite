"""Topology and inventory endpoints (read-only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..deps import get_services
from ..state import Services

router = APIRouter(prefix="/topology", tags=["topology"])

# Approximate geographic positions for the global map (0-1 normalised).
_SITE_POSITIONS = {
    "london": {"x": 0.18, "y": 0.20},
    "newyork": {"x": 0.78, "y": 0.24},
    "bangalore": {"x": 0.30, "y": 0.66},
    "singapore": {"x": 0.74, "y": 0.70},
}


@router.get("/global")
def global_topology(services: Services = Depends(get_services)) -> dict:
    """Sites as nodes + inter-site WAN links as edges, for the global map view."""
    analysis = services.analysis
    graph = services.twin_manager.working_wrapper

    sites = []
    for site_node in graph.get_sites():
        site_id = site_node.get("site") or site_node["id"].replace("site-", "")
        summary = analysis.get_site_summary(site_id)
        sites.append({
            "site": site_id,
            "name": site_node.get("name"),
            "health": summary["health"],
            "device_count": summary["device_count"],
            "devices_down": summary["devices_down"],
            "total_users": summary["total_users"],
            "position": _SITE_POSITIONS.get(site_id, {"x": 0.5, "y": 0.5}),
        })

    # WAN links, mapped to site endpoints and de-duplicated by site pair.
    wan = analysis.get_links(scope="wan")["links"]
    seen: set[frozenset] = set()
    wan_links = []
    for link in wan:
        src_site = analysis.get_device_info(link["source"]).get("site")
        dst_site = analysis.get_device_info(link["target"]).get("site")
        if not src_site or not dst_site or src_site == dst_site:
            continue
        key = frozenset((src_site, dst_site))
        if key in seen:
            continue
        seen.add(key)
        wan_links.append({
            "source_site": src_site,
            "target_site": dst_site,
            "source": link["source"],
            "target": link["target"],
            "link_id": link["link_id"],
            "latency_ms": link["latency_ms"],
            "bandwidth": link["bandwidth"],
            "status": link["status"],
        })

    return {"sites": sites, "wan_links": wan_links}


@router.get("/sites")
def list_sites(services: Services = Depends(get_services)) -> dict:
    """Return all sites with a high-level summary each."""
    graph = services.twin_manager.working_wrapper
    sites = []
    for site_node in graph.get_sites():
        site_id = site_node.get("site") or site_node["id"].replace("site-", "")
        summary = services.analysis.get_site_summary(site_id)
        sites.append({
            "site": site_id,
            "name": site_node.get("name"),
            "region": site_node.get("region"),
            "health": summary["health"],
            "device_count": summary["device_count"],
            "devices_down": summary["devices_down"],
            "total_users": summary["total_users"],
        })
    return {"sites": sites, "total": len(sites)}


@router.get("/sites/{site}")
def site_topology(site: str, services: Services = Depends(get_services)) -> dict:
    return services.analysis.get_site_topology(site)


@router.get("/sites/{site}/summary")
def site_summary(site: str, services: Services = Depends(get_services)) -> dict:
    return services.analysis.get_site_summary(site)


@router.get("/inter-site")
def inter_site(site_a: str = Query(...), site_b: str = Query(...),
               services: Services = Depends(get_services)) -> dict:
    return services.analysis.get_inter_site_connectivity(site_a, site_b)


@router.get("/devices/{device_id}")
def device_info(device_id: str, services: Services = Depends(get_services)) -> dict:
    return services.analysis.get_device_info(device_id)


@router.get("/search")
def search_devices(
    query: str | None = None,
    device_type: str | None = None,
    site: str | None = None,
    status: str | None = None,
    vendor: str | None = None,
    services: Services = Depends(get_services),
) -> dict:
    return services.analysis.search_devices(
        query=query, device_type=device_type, site=site, status=status, vendor=vendor
    )
