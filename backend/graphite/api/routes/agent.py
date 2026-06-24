"""Agent endpoint: investigate a question, optionally streaming via SSE."""

from __future__ import annotations

import json
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..deps import get_services
from ..models import AgentQueryRequest
from ..state import Services

router = APIRouter(prefix="/agent", tags=["agent"])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


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
