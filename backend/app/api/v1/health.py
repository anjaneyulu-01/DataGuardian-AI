"""Liveness endpoint."""

from fastapi import APIRouter

from app.config import settings
from app.schemas import HealthStatus

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthStatus, summary="Service liveness")
async def health() -> HealthStatus:
    """Report that the API process is up.

    Deliberately does not touch PostgreSQL, DataHub, or Gemini — a readiness
    endpoint that checks dependencies gets added alongside those integrations.
    """
    return HealthStatus(
        status="ok",
        version=settings.version,
        environment=settings.environment,
    )
