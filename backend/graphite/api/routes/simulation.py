"""Simulation endpoints: mutate the working twin, inspect, reset."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_services
from ..models import MutateRequest
from ..state import Services

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _mutation_names(services: Services) -> set[str]:
    return {t.name for t in services.mcp_server.list_tools() if t.category == "mutation"}


@router.post("/mutate")
def mutate(req: MutateRequest, services: Services = Depends(get_services)) -> dict:
    """Apply a single mutation (one of the 13 mutation tools) to the working twin.

    Simulation endpoints call the engine directly (operator-facing REST),
    bypassing MCP mode enforcement. The mode is an agent-level concern.
    """
    valid = _mutation_names(services)
    if req.mutation_type not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown mutation_type '{req.mutation_type}'. "
                   f"Valid: {sorted(valid)}",
        )
    method = getattr(services.simulation, req.mutation_type)
    result = method(**req.parameters)
    return {"mutation_type": req.mutation_type, "result": result}


@router.post("/reset")
def reset(services: Services = Depends(get_services)) -> dict:
    services.simulation.reset()
    return {"status": "reset", "mutations_applied": 0}


@router.get("/mutations")
def mutation_log(services: Services = Depends(get_services)) -> dict:
    log = services.simulation.get_mutation_log()
    return {"mutations": log, "total": len(log)}


@router.get("/diff")
def diff(services: Services = Depends(get_services)) -> dict:
    return services.analysis.compare_with_baseline()
