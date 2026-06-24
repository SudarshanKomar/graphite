"""TwinManager — owns the immutable baseline and the mutable working twin.

Lifecycle (ADR-001):
    initialize()      build baseline from JSON (once, at startup)
    clone_working()   deepcopy baseline -> working (discards prior working twin)
    reset()           alias for clone_working()

The baseline graph is never mutated after construction. All simulation and
analysis operate on the working twin.
"""

from __future__ import annotations

import copy

import networkx as nx

from ..errors import TwinNotInitializedError
from .builder import TwinBuilder
from .graph_wrapper import GraphWrapper


class TwinManager:
    """Manages baseline (immutable) and working (mutable) graph twins."""

    def __init__(self, builder: TwinBuilder):
        self._builder = builder
        self._baseline: nx.MultiDiGraph | None = None
        self._working: nx.MultiDiGraph | None = None

    def initialize(self) -> None:
        """Build the baseline graph from JSON. Call once at startup."""
        self._baseline = self._builder.build()

    def clone_working(self) -> None:
        """Deep-copy the baseline into a fresh working twin."""
        if self._baseline is None:
            raise TwinNotInitializedError(
                "Baseline not built — call initialize() before clone_working()"
            )
        self._working = copy.deepcopy(self._baseline)

    def reset(self) -> None:
        """Reset simulation state by re-cloning the working twin from baseline."""
        self.clone_working()

    def has_working(self) -> bool:
        return self._working is not None

    @property
    def baseline(self) -> nx.MultiDiGraph:
        if self._baseline is None:
            raise TwinNotInitializedError("Baseline not built — call initialize() first")
        return self._baseline

    @property
    def working(self) -> nx.MultiDiGraph:
        if self._working is None:
            raise TwinNotInitializedError(
                "Working twin not created — call clone_working() first"
            )
        return self._working

    # Convenience wrappers ------------------------------------------------
    @property
    def baseline_wrapper(self) -> GraphWrapper:
        return GraphWrapper(self.baseline)

    @property
    def working_wrapper(self) -> GraphWrapper:
        return GraphWrapper(self.working)
