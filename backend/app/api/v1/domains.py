"""Domain endpoints.

Domains are the business grouping DataHub uses to organise assets. Assets
outside any domain are a governance gap the agent will flag.
"""

import logging

from fastapi import APIRouter, Path

from app.api.deps import CountQuery, DataHubServiceDep, StartQuery
from app.integrations.datahub import Domain, Page

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("", response_model=Page[Domain], summary="List domains")
async def list_domains(
    service: DataHubServiceDep,
    start: StartQuery = 0,
    count: CountQuery = None,
) -> Page[Domain]:
    """List domains with their owners and asset counts."""
    return await service.get_domains(start=start, count=count)


@router.get(
    "/{urn:path}",
    response_model=Domain,
    summary="Get a domain",
    responses={404: {"description": "The URN does not exist in DataHub."}},
)
async def get_domain(
    service: DataHubServiceDep,
    urn: str = Path(min_length=1, description="Domain URN."),
) -> Domain:
    """Fetch one domain."""
    return await service.get_domain(urn)
