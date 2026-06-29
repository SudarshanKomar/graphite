"""Capability modes for the Graphite MCP server (ADR-007).

Two modes govern agent access to topology-changing tools:

* **observe** (default) — read-only inspection; mutation tools are refused.
* **operate** — full topology control; all tools available.

The MCP server checks the mode before dispatching any tool call.
"""

from __future__ import annotations

from enum import Enum


class Mode(str, Enum):
    """Agent capability mode."""

    OBSERVE = "observe"
    OPERATE = "operate"


class CapabilityMode:
    """Server-side mode state holder.

    V2 MVP: single shared mode across all consumers. Future: per-session.
    """

    def __init__(self) -> None:
        self._current = Mode.OBSERVE

    @property
    def current(self) -> Mode:
        return self._current

    @property
    def current_str(self) -> str:
        return self._current.value

    def switch(self, target: str) -> dict:
        """Switch mode. Returns summary of the transition."""
        try:
            new_mode = Mode(target)
        except ValueError:
            raise ValueError(
                f"Invalid mode '{target}'. Valid modes: "
                f"{', '.join(m.value for m in Mode)}"
            )
        previous = self._current
        self._current = new_mode
        return {
            "previous_mode": previous.value,
            "current_mode": new_mode.value,
            "mutation_tools_enabled": new_mode == Mode.OPERATE,
        }

    def allows_mutation(self) -> bool:
        return self._current == Mode.OPERATE
