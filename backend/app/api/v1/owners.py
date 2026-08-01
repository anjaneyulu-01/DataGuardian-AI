"""Ownership endpoints.

Missing or stale ownership is the single most common governance failure, so
this is one of the first surfaces the agent will call.
"""

import logging

from fastapi import APIRouter, Query

from app.api.deps import DataHubServiceDep, SearchQuery
from app.integrations.datahub import Owner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/owners", tags=["owners"])


@router.get(
    "",
    response_model=list[Owner],
    summary="List owners",
    responses={404: {"description": "The dataset URN does not exist."}},
)
async def list_owners(
    service: DataHubServiceDep,
    dataset_urn: str | None = Query(
        default=None,
        min_length=1,
        description=(
            "Restrict to one dataset's owners. Omit to list every distinct "
            "owner in the catalogue with the number of datasets each owns."
        ),
    ),
    query: SearchQuery = "*",
) -> list[Owner]:
    """List owners, catalogue-wide or for a single dataset.

    Without `dataset_urn` the result comes from a search facet aggregation
    rather than paging every dataset, so it stays cheap on a large catalogue.
    `asset_count` is populated only in that mode.
    """
    return await service.get_owners(dataset_urn=dataset_urn, query=query)
