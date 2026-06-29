"""ReAct agent: a Thought -> Action -> Observation loop (ADR-003).

The agent streams :class:`AgentEvent`s as it reasons. In V2 the agent
dispatches tool calls through the :class:`GraphiteMcpServer` (ADR-006);
mode-based access control (observe/operate) is enforced by the MCP server,
not the agent. Malformed model output is recovered with corrective retries,
and the loop terminates on ``final_answer`` or ``MAX_ITERATIONS``.
"""

from __future__ import annotations

from typing import AsyncGenerator

from ..mcp.server import GraphiteMcpServer, ModeViolation
from .llm.base import LLMProvider
from .parser import AgentParseError, parse_agent_response
from .prompts import (
    build_system_prompt,
    format_max_iterations_notice,
    format_observation,
    format_parse_retry,
)
from .schemas import (
    AgentEvent,
    AgentResponse,
    ErrorEvent,
    FinalAnswerEvent,
    Message,
    ThoughtEvent,
    ToolCallEvent,
    ToolResultEvent,
)

_FINAL_ANSWER = "final_answer"


class ReactAgent:
    """ReAct agent: Thought -> Action -> Observation loop."""

    MAX_ITERATIONS = 15
    MAX_PARSE_RETRIES = 3

    def __init__(self, llm: LLMProvider, mcp_server: GraphiteMcpServer,
                 system_prompt: str | None = None, max_iterations: int | None = None):
        self._llm = llm
        self._mcp = mcp_server
        self._available_tools = mcp_server.list_tools()
        self.max_iterations = max_iterations or self.MAX_ITERATIONS
        self._system_prompt = system_prompt or build_system_prompt(
            self._available_tools, self._mcp.mode.current_str,
            self.max_iterations,
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def run(self, user_query: str) -> AsyncGenerator[AgentEvent, None]:
        """Execute the agent loop, yielding streaming events."""
        messages: list[Message] = [
            Message(role="system", content=self._system_prompt),
            Message(role="user", content=user_query),
        ]

        for _ in range(self.max_iterations):
            try:
                response = await self._next_response(messages)
            except AgentParseError as exc:
                yield ErrorEvent(message=f"Could not parse model output: {exc}")
                return
            except Exception as exc:  # provider / network failure
                yield ErrorEvent(message=f"LLM provider error: {exc}")
                return

            yield ThoughtEvent(content=response.thought)
            action = response.action

            if action.tool == _FINAL_ANSWER:
                yield self._build_final_answer(action.parameters)
                return

            yield ToolCallEvent(tool_name=action.tool, parameters=action.parameters)
            observation = self._execute_tool(action.tool, action.parameters)
            yield ToolResultEvent(tool_name=action.tool, result=observation)
            messages.append(Message(role="user", content=format_observation(action.tool, observation)))

        # Iteration budget exhausted — ask for a final summary, once.
        async for event in self._forced_final(messages):
            yield event

    async def investigate(self, user_query: str) -> dict:
        """Non-streaming convenience: run to completion, return final + trace."""
        events: list[dict] = []
        final: dict | None = None
        async for event in self.run(user_query):
            payload = _event_to_dict(event)
            events.append(payload)
            if payload["type"] == "final_answer":
                final = payload
        return {"final": final, "events": events}

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    async def _next_response(self, messages: list[Message]) -> AgentResponse:
        """Call the LLM and parse, retrying with corrective feedback on failure."""
        last_error: AgentParseError | None = None
        for attempt in range(self.MAX_PARSE_RETRIES):
            result = await self._llm.complete(messages, self._available_tools)
            raw = result.raw_text
            messages.append(Message(role="assistant", content=raw))
            try:
                return parse_agent_response(raw)
            except AgentParseError as exc:
                last_error = exc
                if attempt < self.MAX_PARSE_RETRIES - 1:
                    messages.append(Message(
                        role="user", content=format_parse_retry(raw, str(exc))
                    ))
        raise last_error if last_error else AgentParseError("unknown parse failure")

    def _execute_tool(self, tool: str, parameters: dict) -> dict:
        """Execute a tool via the MCP server.

        Mode enforcement is handled by the MCP server (ADR-007). Unknown tools
        and mode violations are surfaced as structured error observations so the
        agent can adapt.
        """
        try:
            return self._mcp.call_tool(tool, parameters)
        except KeyError:
            return {
                "error": "ToolNotAvailable",
                "message": (
                    f"Tool '{tool}' is not available. Choose one of the "
                    "tools listed in the system prompt, or use 'final_answer'."
                ),
            }
        except ModeViolation as exc:
            return {"error": "ModeViolation", "message": str(exc)}

    def _build_final_answer(self, params: dict) -> FinalAnswerEvent:
        confidence = params.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        remediation = params.get("remediation", [])
        if not isinstance(remediation, list):
            remediation = [str(remediation)]
        affected = params.get("affected_components", {})
        if not isinstance(affected, dict):
            affected = {}
        return FinalAnswerEvent(
            summary=str(params.get("summary", "")),
            root_cause=str(params.get("root_cause", "")),
            affected_components=affected,
            severity=str(params.get("severity", "")),
            confidence=confidence,
            remediation=remediation,
        )

    async def _forced_final(self, messages: list[Message]) -> AsyncGenerator[AgentEvent, None]:
        messages.append(Message(role="user", content=format_max_iterations_notice(self.max_iterations)))
        try:
            response = await self._next_response(messages)
        except Exception:
            yield FinalAnswerEvent(
                summary="Investigation truncated after reaching the maximum number "
                        "of steps; no conclusive answer was reached.",
                root_cause="Inconclusive — iteration budget exhausted.",
                severity="unknown",
                confidence=0.0,
                remediation=["Re-run the investigation with a more specific question."],
            )
            return
        yield ThoughtEvent(content=response.thought)
        if response.action.tool == _FINAL_ANSWER:
            yield self._build_final_answer(response.action.parameters)
        else:
            yield FinalAnswerEvent(
                summary="Investigation truncated after reaching the maximum number of steps.",
                root_cause="Inconclusive — iteration budget exhausted.",
                severity="unknown",
                confidence=0.0,
                remediation=["Re-run the investigation with a more specific question."],
            )


def _event_to_dict(event: AgentEvent) -> dict:
    from dataclasses import asdict

    return asdict(event)
