"""Typed application configuration.

Every value is read from the environment (or a local ``.env`` file) exactly
once, at import time, and validated by Pydantic. Modules should import the
``settings`` singleton rather than calling ``os.getenv`` directly.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# The repository root, resolved from this file rather than the working
# directory: backend/app/config/settings.py -> config -> app -> backend -> root.
# Without this, `uvicorn app.main:app` from backend/ and `pytest` from the repo
# root would read different files.
_REPO_ROOT = Path(__file__).resolve().parents[3]

# The project keeps ONE .env at the repository root, shared by the backend,
# the frontend (via Vite's envDir), and docker-compose. A backend/.env is still
# honoured if present and wins, since later files override earlier ones — but
# it is not required and not created by default.
_ENV_FILES = (_REPO_ROOT / ".env", _REPO_ROOT / "backend" / ".env")


class Settings(BaseSettings):
    """Runtime configuration for the DataGuardian AI backend."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---------------------------------------------------------
    project_name: str = "DataGuardian AI"
    version: str = "0.1.0"
    # `APP_ENV` is accepted as an alias because that is the conventional name
    # on most PaaS platforms, Render included.
    environment: Literal["local", "development", "staging", "production"] = Field(
        default="local",
        validation_alias=AliasChoices(
            "ENVIRONMENT", "APP_ENV", "environment", "app_env"
        ),
    )
    # Left unset, this follows the environment rather than defaulting to True:
    # a production deploy that forgets to set DEBUG must not emit DEBUG logs or
    # verbose errors. Set it explicitly only to override.
    debug: bool | None = None
    api_v1_prefix: str = "/api/v1"

    # --- Server --------------------------------------------------------------
    host: str = "0.0.0.0"
    # Render (and most PaaS) inject the bound port as $PORT.
    port: int = Field(default=8000, validation_alias=AliasChoices("PORT", "port"))

    # --- CORS ----------------------------------------------------------------
    # Browser origins allowed to call this API. The Vite dev server runs on
    # 5173; a deployed frontend MUST be added here or every request fails
    # pre-flight. Accepts a JSON array or a comma-separated list, because
    # PaaS dashboards make JSON awkward to type.
    #
    # Never widened to "*": these endpoints expose catalogue metadata, and a
    # wildcard would let any page on the internet read it from a logged-in
    # browser.
    # `NoDecode` is required, not cosmetic: without it pydantic-settings runs
    # `json.loads` on any list-typed env var BEFORE field validators, so a
    # comma-separated value raises SettingsError at import and the process
    # never starts. NoDecode hands the raw string to the validator below.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Accept `a,b` as well as `["a","b"]`.

        Render's env editor is a single-line text field; requiring valid JSON
        there is a reliable way to produce a deploy that fails only in the
        browser, long after the build went green.
        """
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                # Still allow the JSON form NoDecode just turned off.
                return json.loads(text)
            return [origin.strip() for origin in text.split(",") if origin.strip()]
        return value

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
    # Which provider `LLMFactory` builds.
    #   "auto"  — pick the first provider in `llm_provider_order` that has a
    #             key configured. Nothing to change when you swap keys.
    #   <name>  — pin to that provider and fail loudly if it has no key.
    llm_provider: Literal["auto", "grok", "groq", "gemini", "openai", "claude"] = "auto"

    # Preference order for "auto", and the fail-over order when
    # `llm_fallback_enabled`. Earlier entries win.
    llm_provider_order: list[str] = Field(
        default=["groq", "gemini", "grok", "openai", "claude"]
    )

    # On a *transient* failure (rate limit, timeout, provider down) try the
    # next configured provider instead of failing the request. Deterministic
    # failures — bad key, bad model name — never fail over, because the next
    # provider would fail identically and the real error would be hidden.
    llm_fallback_enabled: bool = True

    # Overrides the active provider's model. Lets you change model without
    # touching provider-specific variables: LLM_MODEL=llama-3.1-8b-instant.
    llm_model: str | None = None

    llm_timeout: float = 60.0
    # Generous because reasoning models (Gemini 2.5, Grok 4) spend part of the
    # budget on internal thinking and return an EMPTY completion if the limit
    # is hit before any visible text is produced.
    llm_max_tokens: int = 4096
    # Low temperature by design: governance explanations must be grounded in
    # the supplied evidence, not creative.
    llm_temperature: float = 0.2
    # Additional attempts after the first, for transient failures only.
    llm_max_retries: int = 2

    # --- xAI / Grok ------------------------------------------------------------
    # NOTE: xAI ("Grok") and Groq below are unrelated companies with similar
    # names. Grok is the model; Groq is an inference host. Keys are not
    # interchangeable: xAI keys start `xai-`, Groq keys start `gsk_`.
    xai_api_key: str | None = None
    xai_model: str = "grok-4-fast-reasoning"
    xai_base_url: str = "https://api.x.ai/v1"

    # --- Groq --------------------------------------------------------------------
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    # Accepts GROQ_BASE_URL or GROQ_API_BASE. Both spellings are in common use
    # in Groq's own docs and examples, and silently ignoring the other one
    # sends requests to the default endpoint while the user believes they
    # overrode it — a genuinely confusing failure.
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        validation_alias=AliasChoices(
            "GROQ_BASE_URL", "GROQ_API_BASE", "groq_base_url", "groq_api_base"
        ),
    )

    # --- Gemini ------------------------------------------------------------------
    # Google exposes an OpenAI-compatible surface at /v1beta/openai, so Gemini
    # reuses the shared transport rather than needing a bespoke provider.
    gemini_api_key: str | None = None
    # 2.5-flash rather than 2.0-flash: they draw on separate quota pools and
    # 2.5 is the current generation.
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai",
        validation_alias=AliasChoices(
            "GEMINI_BASE_URL", "GEMINI_API_BASE", "gemini_base_url", "gemini_api_base"
        ),
    )

    # --- OpenAI --------------------------------------------------------------------
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices(
            "OPENAI_BASE_URL", "OPENAI_API_BASE", "openai_base_url", "openai_api_base"
        ),
    )

    # --- Anthropic / Claude ----------------------------------------------------------
    # Anthropic publishes an OpenAI-compatible compatibility layer, so Claude
    # also reuses the shared transport.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com/v1",
        validation_alias=AliasChoices(
            "ANTHROPIC_BASE_URL",
            "ANTHROPIC_API_BASE",
            "anthropic_base_url",
            "anthropic_api_base",
        ),
    )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def debug_enabled(self) -> bool:
        """Whether to run in debug mode.

        Follows the environment unless `DEBUG` was set explicitly. Deriving it
        means a production deploy cannot accidentally ship DEBUG-level logging
        just because nobody remembered to turn it off.
        """
        if self.debug is not None:
            return self.debug
        return not self.is_production

    @property
    def datahub_graphql_url(self) -> str:
        """Fully-qualified GraphQL endpoint."""
        return f"{self.datahub_gms_url.rstrip('/')}{self.datahub_graphql_path}"

    @property
    def cors_misconfigured(self) -> bool:
        """True when running in production with only localhost origins allowed.

        The single most common deployment failure: the build goes green, the
        health check passes, and every browser request fails pre-flight. The
        lifespan logs a loud warning when this is true.
        """
        if not self.is_production:
            return False
        return all(
            origin.startswith(("http://localhost", "http://127.0.0.1"))
            for origin in self.cors_origins
        )


@lru_cache
def get_settings() -> Settings:
    """Cached accessor, so the environment is parsed only once per process."""
    return Settings()


settings = get_settings()
