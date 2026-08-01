"""Dataset endpoints.

Routers stay thin: validate input, delegate to `DataHubService`, return the
model. No mapping, no error translation — DataHub failures are already typed
exceptions that the handlers in `app.main` render consistently.
"""

import logging

from fastapi import APIRouter, Path

from app.api.deps import CountQuery, DataHubServiceDep, SearchQuery, StartQuery
from app.integrations.datahub import Dataset, DatasetSummary, Page

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get(
    "",
    response_model=Page[DatasetSummary],
    summary="List datasets",
    response_description="A page of datasets with ownership, domain, and tags.",
)
async def list_datasets(
    service: DataHubServiceDep,
    query: SearchQuery = "*",
    start: StartQuery = 0,
    count: CountQuery = None,
) -> Page[DatasetSummary]:
    """List datasets from DataHub.

    Each entry carries the fields the governance rules need — owners,
    description, domain, tags, deprecation — so scanning the catalogue does
    not require a detail call per dataset.
    """
    return await service.get_datasets(query=query, start=start, count=count)


@router.get(
    "/{urn:path}",
    response_model=Dataset,
    summary="Get a dataset",
    responses={404: {"description": "The URN does not exist in DataHub."}},
)
async def get_dataset(
    service: DataHubServiceDep,
    urn: str = Path(
        min_length=1,
        description=(
            "Dataset URN. Contains colons, commas, and parentheses, all legal "
            "in a URL path: "
            "`urn:li:dataset:(urn:li:dataPlatform:hive,my_table,PROD)`."
        ),
    ),
) -> Dataset:
    """Fetch one dataset with its schema, glossary terms, and documentation.

    The schema is included here rather than exposed as a nested route: a
    `{urn:path}` parameter is greedy, so `/datasets/{urn}/schema` could not be
    distinguished from a URN that happens to end in `/schema`.
    """
    return await service.get_dataset(urn)
