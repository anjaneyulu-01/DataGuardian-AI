"""Lineage traversal tool."""

import logging

from app.integrations.datahub import Lineage, LineageDirection
from app.tools.base import DataHubTool

logger = logging.getLogger(__name__)


class LineageTool(DataHubTool):
    """Trace what a dataset depends on and what depends on it."""

    name = "datahub_lineage"
    description = (
        "Trace data lineage for an asset. UPSTREAM shows where its data comes "
        "from; DOWNSTREAM shows what consumes it. Use this to judge the blast "
        "radius of a problem: an issue in a table feeding many downstream "
        "assets matters more than the same issue in an unused one."
    )

    async def get(
        self,
        urn: str,
        direction: str = "DOWNSTREAM",
        count: int = 20,
    ) -> Lineage:
        """Traverse lineage in one direction.

        Args:
            urn: The asset to start from.
            direction: "UPSTREAM" or "DOWNSTREAM". Accepts either case so a
                language model's output does not need normalising upstream.
            count: Maximum nodes to return.

        Returns:
            A `Lineage`. An asset with no lineage yields zero nodes — that is
            a valid answer, not an error.
        """
        return await self._service.get_lineage(
            urn=urn,
            direction=self._parse_direction(direction),
            count=count,
        )

    async def impact(self, urn: str, count: int = 20) -> dict[str, Lineage]:
        """Fetch both directions at once, for impact analysis.

        Returns an object keyed `upstream` and `downstream`.
        """
        return await self._service.get_lineage_both_directions(urn=urn, count=count)

    async def downstream_count(self, urn: str) -> int:
        """How many assets consume this one.

        The single number the agent needs most often when ranking findings by
        severity.
        """
        lineage = await self._service.get_lineage(
            urn=urn, direction=LineageDirection.DOWNSTREAM
        )
        return lineage.total

    @staticmethod
    def _parse_direction(value: str) -> LineageDirection:
        """Coerce a string to the enum with a clear error on a bad value.

        An LLM will occasionally emit "downstream" or "Down". Accepting those
        is cheaper than a failed agent step; anything genuinely wrong still
        fails loudly rather than silently defaulting.
        """
        try:
            return LineageDirection(value.strip().upper())
        except ValueError as exc:
            valid = ", ".join(d.value for d in LineageDirection)
            raise ValueError(
                f"Invalid lineage direction {value!r}. Expected one of: {valid}"
            ) from exc
