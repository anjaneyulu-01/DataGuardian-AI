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

    # --- External services (not wired up yet) --------------------------------
    datahub_gms_url: str = "http://localhost:8080"
    datahub_token: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached accessor, so the environment is parsed only once per process."""
    return Settings()


settings = get_settings()
