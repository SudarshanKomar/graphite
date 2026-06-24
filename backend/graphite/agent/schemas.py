"""Agent message and event schemas (ReAct loop + SSE streaming).

These are the stable data contracts for the agent layer. The ReAct loop itself
is implemented in a later run; this module defines the types it and the API
layer will exchange.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union


# --- Conversation primitives ----------------------------------------------
@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str


@dataclass
class Action:
    """A tool invocation or a final answer."""
    tool: str
    parameters: dict = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Structured response parsed from a single LLM turn."""
    thought: str
    action: Action


# --- Streaming events (for SSE) --------------------------------------------
@dataclass
class ThoughtEvent:
    content: str = ""
    type: str = "thought"


@dataclass
class ToolCallEvent:
    tool_name: str = ""
    parameters: dict = field(default_factory=dict)
    type: str = "tool_call"


@dataclass
class ToolResultEvent:
    tool_name: str = ""
    result: dict = field(default_factory=dict)
    type: str = "tool_result"


@dataclass
class FinalAnswerEvent:
    summary: str = ""
    root_cause: str = ""
    affected_components: dict = field(default_factory=dict)
    severity: str = ""
    confidence: float = 0.0
    remediation: list[str] = field(default_factory=list)
    type: str = "final_answer"


@dataclass
class ErrorEvent:
    message: str = ""
    type: str = "error"


AgentEvent = Union[
    ThoughtEvent, ToolCallEvent, ToolResultEvent, FinalAnswerEvent, ErrorEvent
]
