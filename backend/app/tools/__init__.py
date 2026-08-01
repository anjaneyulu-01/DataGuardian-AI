"""Agent-facing tools over the DataHub integration.

Each tool is a thin wrapper around `DataHubService` with a name, a description,
and narrow primitive-argument methods — the shape a language model needs in
order to call it. They are plain classes with no framework binding: tomorrow's
LangGraph agent adapts them, and nothing here depends on the agent.

Usage:

    from app.tools import build_tools

    tools = build_tools(service)
    page = await tools.datasets.list(count=10)
    impact = await tools.lineage.impact(urn)

Or take a single tool via dependency injection in a router (see
`app.api.deps`).
"""

from dataclasses import dataclass

from app.integrations.datahub import DataHubService
from app.tools.base import DataHubTool
from app.tools.dataset_tool import DatasetTool
from app.tools.domain_tool import DomainTool
from app.tools.lineage_tool import LineageTool
from app.tools.owner_tool import OwnerTool
from app.tools.statistics_tool import StatisticsTool


@dataclass(frozen=True)
class DataHubToolkit:
    """Every tool, sharing one `DataHubService` and therefore one cache."""

    datasets: DatasetTool
    lineage: LineageTool
    owners: OwnerTool
    domains: DomainTool
    statistics: StatisticsTool

    def all(self) -> list[DataHubTool]:
        """Every tool as a list, for bulk registration with an agent."""
        return [self.datasets, self.lineage, self.owners, self.domains, self.statistics]

    def describe(self) -> list[dict[str, str]]:
        """Name and description of each tool, for an LLM tool manifest."""
        return [tool.describe() for tool in self.all()]


def build_tools(service: DataHubService) -> DataHubToolkit:
    """Construct the toolkit from one service instance.

    Sharing a single service means all tools share its cache and connection
    pool, so an agent making five tool calls in one step does not open five
    conversations with DataHub.
    """
    return DataHubToolkit(
        datasets=DatasetTool(service),
        lineage=LineageTool(service),
        owners=OwnerTool(service),
        domains=DomainTool(service),
        statistics=StatisticsTool(service),
    )


__all__ = [
    "DataHubTool",
    "DataHubToolkit",
    "DatasetTool",
    "DomainTool",
    "LineageTool",
    "OwnerTool",
    "StatisticsTool",
    "build_tools",
]
