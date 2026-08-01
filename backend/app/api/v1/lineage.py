"""Lineage endpoints.

Lineage answers the question that turns a governance finding into a priority:
*what breaks if this asset is wrong?* Untagged PII in a table feeding three
executive dashboards matters more than the same issue in an orphaned scratch
table, and this is where that distinction comes from.
"""

import logging

from fastapi import APIRouter, Query

from app.api.deps import CountQuery, DataHubServiceDep, StartQuery, UrnQuery
from app.integrations.datahub import Lineage, LineageDirection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lineage", tags=["lineage"])


@router.get(
    "",
    response_model=Lineage,
    summary="Get lineage in one direction",
    response_description=(
        "Reachable assets, each with its hop distance from the requested URN."
    ),
)
async def get_lineage(
    service: DataHubServiceDep,
    urn: UrnQuery,
    direction: LineageDirection = Query(
        default=LineageDirection.DOWNSTREAM,
        description=(
            "UPSTREAM traces where the data came from; DOWNSTREAM traces what "
            "consumes it."
        ),
    ),
    start: StartQuery = 0,
    count: CountQuery = None,
) -> Lineage:
    """Traverse lineage from one asset.

    An asset with no lineage returns an empty node list rather than a 404 —
    having no upstreams or downstreams is a valid state, and one the staleness
    and orphan rules will look for.
    """
    return await service.get_lineage(
        urn=urn, direction=direction, start=start, count=count
    )


@router.get(
    "/impact",
    response_model=dict[str, Lineage],
    summary="Get lineage in both directions",
    response_description="An object keyed `upstream` and `downstream`.",
)
async def get_impact(
    service: DataHubServiceDep,
    urn: UrnQuery,
    count: CountQuery = None,
) -> dict[str, Lineage]:
    """Fetch both lineage directions in one call.

    Impact analysis always needs both sides, so this saves the caller a round
    trip. DataHub traverses each direction independently, so this is still two
    GraphQL queries.
    """
    return await service.get_lineage_both_directions(urn=urn, count=count)
