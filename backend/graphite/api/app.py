"""FastAPI application factory.

Wires the shared :class:`Services` container onto ``app.state`` and registers
routers plus a single exception handler that maps domain errors to HTTP codes.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..config import Settings, get_settings
from ..errors import (
    GraphiteError,
    InvalidMutation,
)
from .routes import agent, analysis, health, simulation, topology
from .state import Services, build_services


def _status_for(error: GraphiteError) -> int:
    code = getattr(error, "code", "")
    if code.endswith("NotFound") or code == "TwinNotInitialized":
        return 404
    if isinstance(error, InvalidMutation):
        return 409
    return 400


def create_app(settings: Settings | None = None,
               llm_provider: object | None = None,
               services: Services | None = None) -> FastAPI:
    """Create the FastAPI app.

    ``services`` (or ``llm_provider``) may be injected for testing.
    """
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not hasattr(app.state, "services") or app.state.services is None:
            app.state.services = services or build_services(
                settings, llm_provider=llm_provider
            )
        yield

    app = FastAPI(
        title="Graphite — Intelligent Network Copilot",
        version="0.1.0",
        description="Digital-twin network copilot: topology, simulation, and an "
                    "AI agent for root-cause investigation.",
        lifespan=lifespan,
    )

    # Build eagerly too, so TestClient and direct access work before lifespan.
    app.state.services = services or build_services(settings, llm_provider=llm_provider)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(GraphiteError)
    async def graphite_error_handler(request: Request, exc: GraphiteError):
        return JSONResponse(
            status_code=_status_for(exc),
            content={"error": getattr(exc, "code", "GraphiteError"), "message": str(exc)},
        )

    app.include_router(health.router)
    app.include_router(topology.router)
    app.include_router(analysis.router)
    app.include_router(simulation.router)
    app.include_router(agent.router)

    @app.get("/", tags=["health"])
    def root() -> dict:
        return {"name": "graphite", "docs": "/docs", "health": "/health"}

    return app
