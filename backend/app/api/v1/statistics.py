"""Dataset statistics endpoints.

Profiling and usage numbers are what let the agent argue about *risk* rather
than just correctness: a table with 40 million rows and 200 daily queries is a
different problem from an empty one nobody reads.
"""

import logging

from fastapi import APIRouter, Query

from app.api.deps import DataHubServiceDep, UrnQuery
from app.integrations.datahub import DatasetStatistics, TimeRange

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get(
    "",
    response_model=DatasetStatistics,
    summary="Get dataset statistics",
    responses={404: {"description": "The dataset URN does not exist."}},
)
async def get_statistics(
    service: DataHubServiceDep,
    urn: UrnQuery,
    time_range: TimeRange = Query(
        default=TimeRange.MONTH,
        description="Window for usage aggregation.",
    ),
    profile_limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="How many historical profiling snapshots to return.",
    ),
) -> DatasetStatistics:
    """Fetch profiling snapshots and query-usage aggregates for a dataset.

    Both are optional in DataHub and depend on ingestion configuration:

    * `profiles` is empty unless profiling is enabled on the ingestion recipe.
    * `usage` is null unless a usage source is configured. When usage is
      unavailable, `usage_unavailable_reason` explains why instead of failing
      the whole request — an empty result and a broken integration are
      different conditions and the caller must be able to tell them apart.
    """
    return await service.get_statistics(
        urn=urn, time_range=time_range, profile_limit=profile_limit
    )
