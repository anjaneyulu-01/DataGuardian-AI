"""Domain lookup tool."""

# See the note in `owner_tool.py`: the `list` method shadows the builtin
# inside the class body, so later annotations qualify it explicitly.
import builtins
import logging

from app.integrations.datahub import Domain, Page
from app.tools.base import DataHubTool

logger = logging.getLogger(__name__)


class DomainTool(DataHubTool):
    """Inspect the business domains assets are organised into."""

    name = "datahub_domains"
    description = (
        "List the business domains defined in the catalogue, with their "
        "owners and how many assets each contains. Use this to understand how "
        "the organisation groups its data, and to find assets that belong to "
        "no domain."
    )

    async def list(self, start: int = 0, count: int = 20) -> Page[Domain]:
        """List domains with owners and asset counts."""
        return await self._service.get_domains(start=start, count=count)

    async def get(self, urn: str) -> Domain:
        """Fetch one domain.

        Raises:
            DataHubEntityNotFoundError: The URN does not exist.
        """
        return await self._service.get_domain(urn)

    async def names(self) -> builtins.list[str]:
        """Domain names only, for grounding an LLM prompt cheaply.

        Passing the full domain objects into a prompt wastes tokens when all
        the model needs is the vocabulary.
        """
        page = await self._service.get_domains(count=100)
        return [d.name for d in page.results if d.name]
