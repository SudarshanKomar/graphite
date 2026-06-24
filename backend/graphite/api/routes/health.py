"""Health and readiness endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ... import __version__
from ..deps import get_services
from ..models import HealthResponse
from ..state import Services

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(services: Services = Depends(get_services)) -> HealthResponse:
    graph = services.twin_manager.working_wrapper
    return HealthResponse(
        status="ok",
        version=__version__,
        llm_configured=services.llm_available,
        sites=len(graph.get_sites()),
        devices=len(graph.get_devices()),
    )
