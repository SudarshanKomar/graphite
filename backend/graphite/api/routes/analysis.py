"""Read-only analysis endpoints (impact, paths, redundancy)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..deps import get_services
from ..state import Services

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/blast-radius/{component_id}")
def blast_radius(component_id: str, services: Services = Depends(get_services)) -> dict:
    return services.analysis.get_blast_radius(component_id)


@router.get("/service-dependencies/{service_id}")
def service_dependencies(service_id: str, services: Services = Depends(get_services)) -> dict:
    return services.analysis.get_service_dependencies(service_id)


@router.get("/trace")
def trace_route(source: str = Query(...), destination: str = Query(...),
                services: Services = Depends(get_services)) -> dict:
    return services.analysis.trace_route(source, destination)


@router.get("/reachability")
def reachability(source: str = Query(...), destination: str = Query(...),
                 services: Services = Depends(get_services)) -> dict:
    return services.analysis.check_reachability(source, destination)


@router.get("/spof/{site}")
def single_points_of_failure(site: str, services: Services = Depends(get_services)) -> dict:
    return services.analysis.get_single_points_of_failure(site)


@router.get("/redundancy/{component_id}")
def redundancy_status(component_id: str, services: Services = Depends(get_services)) -> dict:
    return services.analysis.get_redundancy_status(component_id)
