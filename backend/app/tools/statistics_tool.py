"""Dataset statistics tool."""

import logging
from typing import Any

from app.integrations.datahub import DatasetStatistics, TimeRange
from app.tools.base import DataHubTool

logger = logging.getLogger(__name__)


class StatisticsTool(DataHubTool):
    """Fetch size and usage numbers that let the agent reason about risk."""

    name = "datahub_statistics"
    description = (
        "Fetch profiling and usage statistics for a dataset: row count, "
        "column count, size, null rates per column, and how many queries and "
        "distinct users it sees. Use this to judge how much a problem matters "
        "— a heavily queried table with millions of rows carries more risk "
        "than an empty one nobody reads. Both kinds of statistics are "
        "optional in DataHub and may be absent."
    )

    async def get(
        self,
        urn: str,
        time_range: str = "MONTH",
        profile_limit: int = 10,
    ) -> DatasetStatistics:
        """Fetch full statistics for a dataset."""
        return await self._service.get_statistics(
            urn=urn,
            time_range=self._parse_range(time_range),
            profile_limit=profile_limit,
        )

    async def summary(self, urn: str, time_range: str = "MONTH") -> dict[str, Any]:
        """A compact, prompt-friendly summary.

        Returns a flat dict rather than the full model: an LLM reasoning about
        risk needs the headline numbers, not every column's percentiles, and
        the full profile can run to hundreds of fields.

        `available` distinguishes "this dataset has no statistics" from "this
        DataHub cannot serve statistics" — the agent must not read absent data
        as a healthy zero.
        """
        stats = await self._service.get_statistics(
            urn=urn, time_range=self._parse_range(time_range)
        )
        profile = stats.latest_profile
        usage = stats.usage

        return {
            "urn": stats.urn,
            "profiled": profile is not None,
            "row_count": profile.row_count if profile else None,
            "column_count": profile.column_count if profile else None,
            "size_in_bytes": profile.size_in_bytes if profile else None,
            "profiled_at": profile.timestamp.isoformat()
            if profile and profile.timestamp
            else None,
            "usage_available": usage is not None,
            "total_queries": usage.total_queries if usage else None,
            "unique_users": usage.unique_users if usage else None,
            "time_range": time_range.upper(),
            "usage_unavailable_reason": stats.usage_unavailable_reason,
        }

    @staticmethod
    def _parse_range(value: str) -> TimeRange:
        """Coerce a string to the enum, tolerating case from an LLM."""
        try:
            return TimeRange(value.strip().upper())
        except ValueError as exc:
            valid = ", ".join(r.value for r in TimeRange)
            raise ValueError(
                f"Invalid time range {value!r}. Expected one of: {valid}"
            ) from exc
