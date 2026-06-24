"""Centralised exception hierarchy for Graphite.

All domain errors derive from :class:`GraphiteError` so callers (tools, API layer)
can catch a single base type. Tool-facing errors carry a stable ``code`` attribute
that mirrors the error names documented in ``specs/schemas/tool-schemas.md``.
"""

from __future__ import annotations


class GraphiteError(Exception):
    """Base class for all Graphite domain errors."""

    code: str = "GraphiteError"


# --- Data / construction ---------------------------------------------------

class ValidationError(GraphiteError):
    """Raised when JSON source data fails validation during twin construction."""

    code = "ValidationError"

    def __init__(self, errors: list[str]):
        self.errors = errors
        joined = "\n  - ".join(errors)
        super().__init__(f"Twin validation failed with {len(errors)} error(s):\n  - {joined}")


class TwinNotInitializedError(GraphiteError):
    """Raised when the working twin is accessed before being cloned."""

    code = "TwinNotInitialized"


# --- Lookup errors ---------------------------------------------------------

class NodeNotFound(GraphiteError):
    code = "NodeNotFound"


class DeviceNotFound(GraphiteError):
    code = "DeviceNotFound"


class LinkNotFound(GraphiteError):
    code = "LinkNotFound"


class VlanNotFound(GraphiteError):
    code = "VlanNotFound"


class ServiceNotFound(GraphiteError):
    code = "ServiceNotFound"


class SiteNotFound(GraphiteError):
    code = "SiteNotFound"


class ComponentNotFound(GraphiteError):
    code = "ComponentNotFound"


class PeerNotFound(GraphiteError):
    code = "PeerNotFound"


class RouteNotFound(GraphiteError):
    code = "RouteNotFound"


# --- State / mutation errors ----------------------------------------------

class InvalidMutation(GraphiteError):
    """Raised when a mutation is invalid for the current state (e.g. already down)."""

    code = "InvalidMutation"


class DeviceAlreadyDown(InvalidMutation):
    code = "DeviceAlreadyDown"


class DeviceAlreadyUp(InvalidMutation):
    code = "DeviceAlreadyUp"


class LinkAlreadyDown(InvalidMutation):
    code = "LinkAlreadyDown"


class LinkAlreadyUp(InvalidMutation):
    code = "LinkAlreadyUp"


class DeviceDown(InvalidMutation):
    code = "DeviceDown"


class VlanAlreadyRemoved(InvalidMutation):
    code = "VlanAlreadyRemoved"


class VlanAlreadyExists(InvalidMutation):
    code = "VlanAlreadyExists"


class PeerAlreadyDown(InvalidMutation):
    code = "PeerAlreadyDown"


class PeerAlreadyUp(InvalidMutation):
    code = "PeerAlreadyUp"


class InvalidLatency(InvalidMutation):
    code = "InvalidLatency"


class RouteConflict(InvalidMutation):
    code = "RouteConflict"


class InvalidNextHop(InvalidMutation):
    code = "InvalidNextHop"


class PrefixNotFound(GraphiteError):
    code = "PrefixNotFound"


class PrefixAlreadyAdvertised(InvalidMutation):
    code = "PrefixAlreadyAdvertised"


# --- Tool errors -----------------------------------------------------------

class ToolNotFound(GraphiteError):
    code = "ToolNotFound"


class ToolExecutionError(GraphiteError):
    code = "ToolExecutionError"
