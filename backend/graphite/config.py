"""Application configuration (env-driven, single source of truth).

Values are read from environment variables (and a local ``.env`` if present).
Defaults match ``.env.example`` so the backend boots without a real key — the
agent endpoints simply report that no LLM is configured.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Graphite backend settings."""

    model_config = SettingsConfigDict(
        env_prefix="GRAPHITE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- LLM ---------------------------------------------------------------
    # GEMINI_API_KEY is read without the GRAPHITE_ prefix (validation_alias bypasses
    # env_prefix); GRAPHITE_GEMINI_API_KEY is also accepted.
    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEY", "GRAPHITE_GEMINI_API_KEY"),
    )
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.1
    # On HTTP 429 (rate limit), wait the server-suggested delay (capped) and retry.
    # One retry keeps a transient per-minute limit recoverable without long hangs.
    llm_max_retries: int = 1
    llm_retry_cap_seconds: float = 65.0

    # --- Data --------------------------------------------------------------
    data_dir: str = "network_state"

    # --- API ---------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # --- Agent -------------------------------------------------------------
    # Live investigations observed to complete in 1-3 tool calls; 10 leaves ample
    # headroom while bounding API usage (tuned down from 15 after real testing).
    agent_max_iterations: int = 10

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir)
        return p if p.is_absolute() else _BACKEND_ROOT / p

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_configured(self) -> bool:
        return bool(self.gemini_api_key)


def _read_gemini_key() -> str:
    """GEMINI_API_KEY is conventionally unprefixed; read it directly."""
    import os

    return os.environ.get("GEMINI_API_KEY", "")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.gemini_api_key:
        # Allow the unprefixed GEMINI_API_KEY (matches .env.example).
        key = _read_gemini_key()
        if key:
            settings.gemini_api_key = key
    return settings
