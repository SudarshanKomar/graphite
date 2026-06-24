"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from graphite.analysis import AnalysisEngine
from graphite.simulation import SimulationEngine
from graphite.tools import ToolContext, build_default_registry
from graphite.twin import TwinBuilder, TwinManager

DATA_DIR = Path(__file__).resolve().parent.parent / "network_state"


@pytest.fixture(scope="session")
def baseline_manager() -> TwinManager:
    """Build the baseline once per session (expensive); never mutated."""
    mgr = TwinManager(TwinBuilder(DATA_DIR))
    mgr.initialize()
    return mgr


@pytest.fixture
def twin(baseline_manager) -> TwinManager:
    """Fresh working twin per test (cheap deepcopy of the shared baseline)."""
    baseline_manager.clone_working()
    return baseline_manager


@pytest.fixture
def analysis(twin) -> AnalysisEngine:
    return AnalysisEngine(twin)


@pytest.fixture
def sim(twin) -> SimulationEngine:
    return SimulationEngine(twin)


@pytest.fixture
def registry(twin, sim, analysis):
    ctx = ToolContext(simulation_engine=sim, analysis_engine=analysis, twin_manager=twin)
    return build_default_registry(ctx)
