"""FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import (
    DATAHUB_CACHE_STATE_KEY,
    DATAHUB_CLIENT_STATE_KEY,
    LLM_PROVIDER_STATE_KEY,
)
from app.api.v1 import api_router
from app.config import settings
from app.core import configure_logging, register_exception_handlers
from app.integrations.datahub import DataHubClient
from app.integrations.datahub.cache import NullCache, TTLCache
from app.llm import LLMError, LLMFactory
from app.scheduler import shutdown_scheduler, start_scheduler
from app.schemas import ServiceInfo

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start and stop process-wide resources around the server's lifetime."""
    configure_logging()
    logger.info(
        "Starting %s v%s (environment=%s)",
        settings.project_name,
        settings.version,
        settings.environment,
    )

    # One DataHub client per process, sharing a connection pool across all
    # requests. Constructing it never performs I/O, so a DataHub that is down
    # does not prevent the API from starting — calls fail individually with a
    # typed error instead.
    datahub_client = DataHubClient(settings=settings)
    setattr(app.state, DATAHUB_CLIENT_STATE_KEY, datahub_client)

    # Process-wide metadata cache. Must outlive a request, so it lives here
    # rather than being built per dependency resolution.
    datahub_cache: TTLCache = (
        TTLCache(
            ttl_seconds=settings.datahub_cache_ttl_seconds,
            max_entries=settings.datahub_cache_max_entries,
        )
        if settings.datahub_cache_enabled
        else NullCache()
    )
    setattr(app.state, DATAHUB_CACHE_STATE_KEY, datahub_cache)

    logger.info(
        "DataHub client ready (gms_url=%s, authenticated=%s, cache=%s)",
        datahub_client.base_url,
        datahub_client.is_authenticated,
        f"{settings.datahub_cache_ttl_seconds:g}s TTL"
        if settings.datahub_cache_enabled
        else "disabled",
    )
    if not datahub_client.is_authenticated:
        logger.warning(
            "DATAHUB_TOKEN is not set. This works against a local quickstart "
            "with metadata-service auth disabled, but any secured instance "
            "will reject these calls."
        )

    # One LLM provider per process. Construction performs no I/O and does not
    # require an API key, so a missing key never blocks startup — calls fail
    # individually with a configuration error, and /health reports it.
    try:
        llm = LLMFactory.create(settings)
        setattr(app.state, LLM_PROVIDER_STATE_KEY, llm)

        # Report what the factory ACTUALLY built. Reading `settings.xai_*`
        # here was wrong: with LLM_PROVIDER=auto the selected provider may be
        # any of five, so the log claimed an xAI model and "configured=False"
        # while a perfectly healthy Groq provider was serving requests.
        available = LLMFactory.available_providers(settings)
        logger.info(
            "LLM ready (provider=%s, model=%s, configured=%s%s)",
            llm.name,
            getattr(llm, "model", "unknown"),
            bool(available),
            f", chain={getattr(llm, 'chain', [])}" if len(available) > 1 else "",
        )
        if not available:
            hint = ", ".join(f"{name.upper()}_API_KEY" for name in ("groq", "gemini"))
            logger.warning(
                "No LLM provider has an API key. The API starts normally, but "
                "any LLM-backed endpoint will return a configuration error "
                "until one of %s is set in the .env at the repository root.",
                hint,
            )
    except LLMError as exc:
        # A misconfigured LLM_PROVIDER must not take the whole API down —
        # every DataHub endpoint still works without it.
        logger.error("LLM provider unavailable: %s", exc.detail)

    start_scheduler()

    yield

    shutdown_scheduler()
    await datahub_client.aclose()

    # Release the LLM connection pool if a provider was built.
    provider = getattr(app.state, LLM_PROVIDER_STATE_KEY, None)
    closer = getattr(provider, "aclose", None)
    if callable(closer):
        await closer()

    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description=(
        "Autonomous AI agent that monitors DataHub metadata, detects governance "
        "issues, explains the risk, and recommends corrective action."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", response_model=ServiceInfo, tags=["system"], summary="Service root")
async def root() -> ServiceInfo:
    """Identify the service. Used as the smoke test that the API is up."""
    return ServiceInfo(project=settings.project_name, status="running")
