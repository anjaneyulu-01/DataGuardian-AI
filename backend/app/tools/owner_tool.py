"""Ownership lookup tool."""

# This class defines a method named `list`, which shadows the builtin inside
# the class body, so annotations after it must say `builtins.list[...]`. The
# method name is part of the tool's public API (`OwnerTool.list()`), so
# qualifying the annotation beats renaming the method.
import builtins
import logging

from app.integrations.datahub import Owner
from app.tools.base import DataHubTool

logger = logging.getLogger(__name__)


class OwnerTool(DataHubTool):
    """Answer who is responsible for an asset."""

    name = "datahub_owners"
    description = (
        "List data owners. Called with a dataset URN it returns that "
        "dataset's owners; called with no arguments it returns every distinct "
        "owner in the catalogue with how many assets each owns. Use this to "
        "find who to notify about an issue, and to spot assets with no owner."
    )

    async def list(
        self, dataset_urn: str | None = None, query: str = "*"
    ) -> builtins.list[Owner]:
        """List owners, catalogue-wide or for one dataset.

        Args:
            dataset_urn: Restrict to a single dataset. Omit for the
                catalogue-wide aggregation, which is the only mode that
                populates `asset_count`.
            query: Search filter for the aggregation mode.
        """
        return await self._service.get_owners(dataset_urn=dataset_urn, query=query)

    async def for_dataset(self, urn: str) -> builtins.list[Owner]:
        """Owners of one dataset. Empty list means genuinely unowned."""
        return await self._service.get_owners(dataset_urn=urn)

    async def has_owner(self, urn: str) -> bool:
        """Whether a dataset has any owner at all."""
        return bool(await self._service.get_owners(dataset_urn=urn))
