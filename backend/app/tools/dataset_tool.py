"""Dataset lookup tool."""

# See the note in `owner_tool.py`: the `list` method shadows the builtin
# inside the class body, so later annotations qualify it explicitly.
import builtins
import logging

from app.integrations.datahub import Dataset, DatasetSummary, Page
from app.tools.base import DataHubTool

logger = logging.getLogger(__name__)


class DatasetTool(DataHubTool):
    """Find and inspect datasets catalogued in DataHub."""

    name = "datahub_datasets"
    description = (
        "List or search datasets in the data catalogue, or fetch one dataset "
        "in full. Each dataset includes its owners, description, domain, "
        "tags, and deprecation status. Use this to find assets and to check "
        "what metadata they are missing."
    )

    async def list(
        self, query: str = "*", start: int = 0, count: int = 20
    ) -> Page[DatasetSummary]:
        """List datasets.

        Args:
            query: DataHub search syntax; `*` matches everything.
            start: Zero-based offset for paging.
            count: Page size. Clamped server-side.
        """
        return await self._service.get_datasets(query=query, start=start, count=count)

    async def get(self, urn: str) -> Dataset:
        """Fetch one dataset in full, including its schema.

        Raises:
            DataHubEntityNotFoundError: The URN does not exist.
        """
        return await self._service.get_dataset(urn)

    async def search(self, query: str, count: int = 20) -> Page[DatasetSummary]:
        """Free-text search across datasets."""
        return await self._service.search(query=query, count=count)

    async def list_undocumented(self, count: int = 50) -> builtins.list[DatasetSummary]:
        """Return datasets from the first page that have no description.

        A convenience filter over `list`, not a governance rule: it reports
        what DataHub holds and applies no severity or judgement. The rule
        engine decides whether a missing description matters for a given
        asset.
        """
        page = await self._service.get_datasets(count=count)
        return [d for d in page.results if not d.description]

    async def list_unowned(self, count: int = 50) -> builtins.list[DatasetSummary]:
        """Return datasets from the first page that have no owner.

        Same caveat as `list_undocumented`: a filter, not a verdict.
        """
        page = await self._service.get_datasets(count=count)
        return [d for d in page.results if not d.owners]
