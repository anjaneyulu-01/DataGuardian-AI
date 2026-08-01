"""Liveness and dependency-readiness endpoints.

The two are deliberately separate:

* `/health` answers "is this process alive?" It touches nothing external, so
  it stays fast and cannot be made red by a third party. Container
  orchestrators restart on this.
* `/health/datahub` and `/health/llm` answer "can this process do useful
  work?" They call the dependency and report what they found. Never restart
  on these — a third-party outage is not a reason to kill the API.
"""

import logging

from fastapi import APIRouter

from app.api.deps import DataHubServiceDep, LLMDep
from app.config import settings
from app.integrations.datahub import DataHubHealth
from app.llm import LLMHealth
from app.schemas import HealthStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthStatus, summary="Service liveness")
async def health() -> HealthStatus:
    """Report that the API process is up.

    Deliberately does not touch PostgreSQL, DataHub, or Gemini — see
    `/health/datahub` for dependency status.
    """
    return HealthStatus(
        status="ok",
        version=settings.version,
        environment=settings.environment,
    )


class DataHubHealthReport(DataHubHealth):
    """`DataHubHealth` plus this process's metadata-cache counters.

    Additive subclass: every `DataHubHealth` field is unchanged, so existing
    consumers are unaffected.
    """

    cache: dict[str, float | int] | None = None


@router.get(
    "/health/datahub",
    response_model=DataHubHealthReport,
    summary="DataHub connectivity",
    response_description=(
        "Connectivity report. Always HTTP 200 — read the `reachable` field."
    ),
)
async def datahub_health(service: DataHubServiceDep) -> DataHubHealthReport:
    """Probe the configured DataHub instance.

    Returns 200 even when DataHub is down, with `reachable: false` and an
    `error` describing why. A monitoring endpoint that returns 502 tells an
    operator strictly less than one that says which URL it tried, whether a
    token was configured, and what the failure was.

    Also reports the in-process metadata cache counters, since "is the data
    fresh or cached?" is the first question when debugging staleness.
    """
    health = await service.check_health()
    stats = service.cache_stats
    return DataHubHealthReport(
        **health.model_dump(),
        cache={
            "hits": stats.hits,
            "misses": stats.misses,
            "entries": stats.entries,
            "evictions": stats.evictions,
            "hit_rate": round(stats.hit_rate, 4),
        },
    )


@router.get(
    "/health/llm",
    response_model=LLMHealth,
    summary="LLM provider connectivity",
    response_description=(
        "Provider report. Always HTTP 200 — read `configured` and `reachable`."
    ),
)
async def llm_health(llm: LLMDep) -> LLMHealth:
    """Probe the configured LLM provider.

    Distinguishes two states an operator must not confuse: `configured: false`
    means no API key is set (a local setup problem), while `reachable: false`
    with `configured: true` means the key exists but the provider could not be
    reached or rejected it. The probe spends no tokens.
    """
    return await llm.health()
