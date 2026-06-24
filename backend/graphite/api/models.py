"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MutateRequest(BaseModel):
    """Apply a single mutation to the working twin."""

    mutation_type: str = Field(..., description="One of the 13 mutation tool names")
    parameters: dict = Field(default_factory=dict)


class AgentQueryRequest(BaseModel):
    """Ask the agent to investigate a natural-language question."""

    query: str = Field(..., min_length=1)
    stream: bool = Field(True, description="Stream events via SSE when true")


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_configured: bool
    sites: int
    devices: int
