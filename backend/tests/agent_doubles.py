"""Test doubles for the agent.

Stand in for the LLM and the Tool layer so graph tests run with no network and
no DataHub, while still exercising the real planner, real risk engine, real
nodes, and the real compiled LangGraph.

These are doubles, not fixtures of sample data: they record what was called,
which is how "the agent skipped the lineage tool" becomes an assertion.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.agents.state import Recommendation
from app.integrations.datahub import (
    DatasetSummary,
    Lineage,
    LineageDirection,
    Owner,
    OwnerKind,
    Page,
)
from app.llm.base import BaseLLM
from app.llm.models import ChatMessage, LLMHealth, LLMResponse, TokenUsage
from app.tools import DataHubToolkit
from app.tools.base import DataHubTool


class StubLLM(BaseLLM):
    """An LLM that returns a canned reply, or always fails.

    `structured_output` is overridden rather than inherited so tests do not
    depend on the model emitting parseable JSON — the parsing path has its own
    tests in the LLM suite.
    """

    name = "stub"

    def __init__(
        self,
        reply: str = "ok",
        error: Exception | None = None,
        structured: dict[str, Any] | None = None,
    ) -> None:
        self._reply = reply
        self._error = error
        self._structured = structured
        self.calls = 0
        self.prompts: list[str] = []
        self.closed = False

    @property
    def model(self) -> str:
        return "stub-model"

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self.calls += 1
        self.prompts.append(messages[-1].content if messages else "")
        if self._error is not None:
            raise self._error
        return LLMResponse(
            text=self._reply,
            provider=self.name,
            model=self.model,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5),
            latency_ms=1.0,
        )

    async def structured_output(  # type: ignore[override]
        self,
        prompt: str,
        schema: type[BaseModel],
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        self.calls += 1
        self.prompts.append(prompt)
        if self._error is not None:
            raise self._error
        if self._structured is not None:
            return schema.model_validate(self._structured)
        return schema.model_validate(_default_for(schema))

    async def health(self) -> LLMHealth:
        return LLMHealth(
            provider=self.name, configured=True, reachable=True, model=self.model
        )

    async def aclose(self) -> None:
        self.closed = True


def _default_for(schema: type[BaseModel]) -> dict[str, Any]:
    """Minimal valid instance of any node's output schema."""
    values: dict[str, Any] = {}
    for field_name, field in schema.model_fields.items():
        annotation = field.annotation
        if annotation is str or annotation == (str | None):
            values[field_name] = f"stub {field_name}"
        elif annotation == list[str]:
            values[field_name] = [f"stub {field_name} 1"]
        else:
            # Nested model lists (e.g. recommendations).
            values[field_name] = []
    return values


# ---------------------------------------------------------------------------
# Tool-layer doubles
# ---------------------------------------------------------------------------


def make_dataset(
    name: str = "fct_orders",
    *,
    owned: bool = True,
    documented: bool = True,
    downstream: int = 0,
    pii_column: bool = False,
) -> DatasetSummary:
    """Build a `DatasetSummary` with chosen governance properties."""
    return DatasetSummary(
        urn=f"urn:li:dataset:(urn:li:dataPlatform:snowflake,{name},PROD)",
        name=name,
        qualified_name=f"prod.analytics.{name}",
        description="A documented asset." if documented else None,
        owners=(
            [Owner(urn="urn:li:corpuser:ana", kind=OwnerKind.USER, name="ana")]
            if owned
            else []
        ),
        tags=[],
    )


class _RecordingTool:
    """Base for tool doubles that record their calls."""

    def __init__(self) -> None:
        self.calls: list[str] = []


class FakeDatasetTool(_RecordingTool):
    def __init__(self, datasets: list[DatasetSummary], error: Exception | None = None):
        super().__init__()
        self._datasets = datasets
        self._error = error

    async def list(self, query: str = "*", start: int = 0, count: int = 20):
        self.calls.append("list")
        if self._error:
            raise self._error
        return Page[DatasetSummary](
            start=0,
            count=len(self._datasets),
            total=len(self._datasets),
            results=self._datasets,
        )

    async def search(self, query: str, count: int = 20):
        self.calls.append(f"search:{query}")
        if self._error:
            raise self._error
        matches = [d for d in self._datasets if query in (d.name or "")]
        return Page[DatasetSummary](
            start=0, count=len(matches), total=len(matches), results=matches
        )

    async def get(self, urn: str):
        self.calls.append(f"get:{urn}")
        if self._error:
            raise self._error
        return self._datasets[0]


class FakeOwnerTool(_RecordingTool):
    def __init__(
        self, owners: list[Owner] | None = None, error: Exception | None = None
    ):
        super().__init__()
        self._owners = owners or []
        self._error = error

    async def list(self, dataset_urn: str | None = None, query: str = "*"):
        self.calls.append("list")
        if self._error:
            raise self._error
        return self._owners

    async def for_dataset(self, urn: str):
        self.calls.append(f"for_dataset:{urn}")
        if self._error:
            raise self._error
        return self._owners


class FakeLineageTool(_RecordingTool):
    def __init__(self, downstream_total: int = 0, error: Exception | None = None):
        super().__init__()
        self._downstream_total = downstream_total
        self._error = error

    async def impact(self, urn: str, count: int = 20):
        self.calls.append(f"impact:{urn}")
        if self._error:
            raise self._error
        return {
            "upstream": Lineage(urn=urn, direction=LineageDirection.UPSTREAM, total=0),
            "downstream": Lineage(
                urn=urn,
                direction=LineageDirection.DOWNSTREAM,
                total=self._downstream_total,
            ),
        }


class FakeStatisticsTool(_RecordingTool):
    def __init__(self, error: Exception | None = None):
        super().__init__()
        self._error = error

    async def summary(self, urn: str, time_range: str = "MONTH") -> dict[str, Any]:
        self.calls.append(f"summary:{urn}")
        if self._error:
            raise self._error
        return {
            "urn": urn,
            "profiled": True,
            "row_count": 1000,
            "column_count": 8,
            "usage_available": False,
        }


def make_toolkit(
    datasets: list[DatasetSummary] | None = None,
    owners: list[Owner] | None = None,
    downstream_total: int = 0,
    dataset_error: Exception | None = None,
    lineage_error: Exception | None = None,
) -> DataHubToolkit:
    """Assemble a toolkit of doubles shaped like the real one."""
    return DataHubToolkit(
        datasets=FakeDatasetTool(  # type: ignore[arg-type]
            datasets if datasets is not None else [make_dataset()], dataset_error
        ),
        owners=FakeOwnerTool(owners),  # type: ignore[arg-type]
        lineage=FakeLineageTool(downstream_total, lineage_error),  # type: ignore[arg-type]
        domains=None,  # type: ignore[arg-type] - no node uses it
        statistics=FakeStatisticsTool(),  # type: ignore[arg-type]
    )


def called_tools(toolkit: DataHubToolkit) -> set[str]:
    """Which tool doubles were invoked — the basis for skip assertions."""
    used: set[str] = set()
    for attribute in ("datasets", "owners", "lineage", "statistics"):
        tool = getattr(toolkit, attribute, None)
        if tool is not None and getattr(tool, "calls", None):
            used.add(attribute)
    return used


__all__ = [
    "DataHubTool",
    "FakeDatasetTool",
    "FakeLineageTool",
    "FakeOwnerTool",
    "FakeStatisticsTool",
    "Recommendation",
    "StubLLM",
    "called_tools",
    "json",
    "make_dataset",
    "make_toolkit",
]
