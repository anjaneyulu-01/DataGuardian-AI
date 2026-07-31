"""FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config import settings
from app.core import configure_logging, register_exception_handlers
from app.scheduler import shutdown_scheduler, start_scheduler
from app.schemas import ServiceInfo

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Start and stop process-wide resources around the server's lifetime."""
    configure_logging()
    logger.info(
        "Starting %s v%s (environment=%s)",
        settings.project_name,
        settings.version,
        settings.environment,
    )
    start_scheduler()

    yield

    shutdown_scheduler()
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
