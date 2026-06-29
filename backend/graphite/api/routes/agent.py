"""Agent endpoint: investigate a question, optionally streaming via SSE.

V2 adds capability mode switching (observe / operate) via ``/agent/mode``.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..deps import get_services
from ..models import AgentQueryRequest
from ..state import Services

router = APIRouter(prefix="/agent", tags=["agent"])


class ModeRequest(BaseModel):
    mode: str = Field(..., pattern="^(observe|operate)$")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


@router.get("/mode")
def get_mode(services: Services = Depends(get_services)) -> dict:
    """Return the current capability mode."""
    return {
        "mode": services.mcp_server.mode.current_str,
        "mutation_tools_enabled": services.mcp_server.mode.allows_mutation(),
    }


@router.post("/mode")
def set_mode(req: ModeRequest, services: Services = Depends(get_services)) -> dict:
    """Switch capability mode (observe / operate)."""
    return services.mcp_server.mode.switch(req.mode)


@router.post("/query")
async def query(req: AgentQueryRequest, services: Services = Depends(get_services)):
    if not services.llm_available:
        raise HTTPException(
            status_code=503,
            detail="No LLM provider configured. Set GEMINI_API_KEY to enable the agent.",
        )
    agent = services.make_agent()

    if not req.stream:
        return await agent.investigate(req.query)

    async def event_stream():
        try:
            async for event in agent.run(req.query):
                yield _sse(asdict(event))
        except Exception as exc:  # safety net — surface as an error event
            yield _sse({"type": "error", "message": f"Agent failure: {exc}"})
        yield _sse({"type": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
