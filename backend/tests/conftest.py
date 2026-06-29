"""Shared pytest fixtures (V2 — MCP-native)."""

from pathlib import Path

import pytest

from graphite.analysis import AnalysisEngine
from graphite.mcp import GraphiteMcpServer
from graphite.simulation import SimulationEngine
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
def mcp_server(twin, sim, analysis) -> GraphiteMcpServer:
    """V2 MCP server wired to fresh engines."""
    return GraphiteMcpServer(analysis, sim, twin)
