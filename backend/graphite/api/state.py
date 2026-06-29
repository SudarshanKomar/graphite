"""Application service container and wiring (V2 — MCP-native).

Builds the single shared object graph (twin → engines → MCP server →
LLM provider) used by all API routes. A fresh :class:`ReactAgent` is created
per request (cheap), but the heavy components are built once at startup.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..agent.react_agent import ReactAgent
from ..analysis import AnalysisEngine
from ..config import Settings, get_settings
from ..mcp import GraphiteMcpServer
from ..simulation import SimulationEngine
from ..twin import TwinBuilder, TwinManager


@dataclass
class Services:
    """Container for the shared backend services."""

    settings: Settings
    twin_manager: TwinManager
    analysis: AnalysisEngine
    simulation: SimulationEngine
    mcp_server: GraphiteMcpServer
    llm_provider: object | None = None

    @property
    def llm_available(self) -> bool:
        return self.llm_provider is not None

    def make_agent(self) -> ReactAgent:
        if self.llm_provider is None:
            raise RuntimeError("No LLM provider configured (set GEMINI_API_KEY)")
        return ReactAgent(
            self.llm_provider,
            self.mcp_server,
            max_iterations=self.settings.agent_max_iterations,
        )


def _build_llm_provider(settings: Settings):
    """Construct the configured LLM provider, or None if unavailable."""
    if not settings.llm_configured:
        return None
    if settings.llm_provider == "gemini":
        from ..agent.llm.gemini_provider import GeminiProvider

        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_retries=settings.llm_max_retries,
            retry_cap_seconds=settings.llm_retry_cap_seconds,
        )
    return None


def build_services(settings: Settings | None = None,
                   llm_provider: object | None = None) -> Services:
    """Build and wire all services. ``llm_provider`` overrides the configured one."""
    settings = settings or get_settings()

    twin_manager = TwinManager(TwinBuilder(settings.data_path))
    twin_manager.initialize()
    twin_manager.clone_working()

    analysis = AnalysisEngine(twin_manager)
    simulation = SimulationEngine(twin_manager)
    mcp_server = GraphiteMcpServer(analysis, simulation, twin_manager)

    provider = llm_provider if llm_provider is not None else _build_llm_provider(settings)

    return Services(
        settings=settings,
        twin_manager=twin_manager,
        analysis=analysis,
        simulation=simulation,
        mcp_server=mcp_server,
        llm_provider=provider,
    )
