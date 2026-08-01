"""Typed application configuration.

Every value is read from the environment (or a local ``.env`` file) exactly
once, at import time, and validated by Pydantic. Modules should import the
``settings`` singleton rather than calling ``os.getenv`` directly.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the DataGuardian AI backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---------------------------------------------------------
    project_name: str = "DataGuardian AI"
    version: str = "0.1.0"
    environment: Literal["local", "development", "staging", "production"] = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # --- Server --------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # --- CORS ----------------------------------------------------------------
    # Origins allowed to call the API from a browser. The Vite dev server runs
    # on 5173; add deployed frontend origins here.
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # --- Database ------------------------------------------------------------
    database_url: str = (
        "postgresql+psycopg2://dataguardian:dataguardian@localhost:5432/dataguardian"
    )
    db_echo: bool = False

    # --- Scheduler -----------------------------------------------------------
    scheduler_enabled: bool = False
    scan_interval_minutes: int = 60

    # --- DataHub -------------------------------------------------------------
    # Base URL of the DataHub GMS service. When talking through the DataHub
    # frontend proxy (port 9002) this is usually `http://localhost:9002/api/gms`
    # instead of the GMS port directly.
    datahub_gms_url: str = "http://localhost:8080"
    # Personal access token. Optional: an unsecured local quickstart accepts
    # unauthenticated calls, but any real deployment requires this.
    datahub_token: str | None = None
    # Path of the GraphQL endpoint, relative to `datahub_gms_url`.
    datahub_graphql_path: str = "/api/graphql"
    datahub_timeout_seconds: float = 30.0
    # Retries apply only to transient failures (connection refused, timeout,
    # 429/502/503/504). Auth failures and GraphQL errors are deterministic and
    # are never retried. Every operation here is a read, so replay is safe.
    # This is the number of *additional* attempts after the first.
    datahub_max_retries: int = 2
    datahub_retry_base_delay_seconds: float = 0.5
    datahub_retry_max_delay_seconds: float = 8.0

    # --- DataHub cache -------------------------------------------------------
    # Metadata changes on an ingestion cadence, not per request, so a short TTL
    # removes most GMS round-trips without serving stale governance data.
    datahub_cache_enabled: bool = True
    datahub_cache_ttl_seconds: float = 60.0
    datahub_cache_max_entries: int = 512
    # Upper bound on `count` for any paginated DataHub call, so a caller cannot
    # ask GMS for an unbounded page.
    datahub_max_page_size: int = 200
    datahub_default_page_size: int = 20
    datahub_verify_ssl: bool = True

    # --- LLM -------------------------------------------------------------------
    # Which provider `LLMFactory` builds. Only "grok" is implemented; "gemini",
    # "openai", and "claude" are registered placeholders so switching later is
    # a config change, not a code change.
    llm_provider: Literal["grok", "gemini", "openai", "claude"] = "grok"
    llm_timeout: float = 60.0
    llm_max_tokens: int = 4096
    # Low temperature by design: governance explanations must be grounded in
    # the supplied evidence, not creative.
    llm_temperature: float = 0.2
    # Additional attempts after the first, for transient failures only.
    llm_max_retries: int = 2

    # --- xAI / Grok ------------------------------------------------------------
    xai_api_key: str | None = None
    xai_model: str = "grok-4-fast-reasoning"
    xai_base_url: str = "https://api.x.ai/v1"

    # --- Gemini (placeholder provider — not implemented yet) --------------------
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def datahub_graphql_url(self) -> str:
        """Fully-qualified GraphQL endpoint."""
        return f"{self.datahub_gms_url.rstrip('/')}{self.datahub_graphql_path}"


@lru_cache
def get_settings() -> Settings:
    """Cached accessor, so the environment is parsed only once per process."""
    return Settings()


settings = get_settings()
