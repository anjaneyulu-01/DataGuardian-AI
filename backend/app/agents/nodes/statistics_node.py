"""Statistics node — size and usage, for weighting risk by real consumption.

Optional data by nature: profiling and usage both depend on ingestion
configuration most instances do not have. This node therefore treats absence
as a normal outcome and records it explicitly, so the LLM is told "unknown"
rather than being left to infer a healthy zero.
"""

from __future__ import annotations

from typing import Any

from app.agents.executor import NodeFn, run_node
from app.agents.state import AgentState


def make_statistics_node(tools: Any) -> NodeFn:
    """Build the statistics node bound to a toolkit."""

    async def statistics_node(state: AgentState) -> dict[str, Any]:
        async def body(current: AgentState) -> dict[str, Any]:
            urn = current.get("target_urn") or _first_dataset_urn(current)
            if not urn:
                return {
                    "statistics": {"available": False, "reason": "no asset in scope"}
                }

            # `summary()` returns a flat, prompt-sized dict and already
            # distinguishes "not profiled" from "profiled as empty".
            summary = await tools.statistics.summary(urn)
            return {"statistics": {**summary, "available": True}}

        return await run_node("statistics", state, body)

    return statistics_node


def _first_dataset_urn(state: AgentState) -> str | None:
    for dataset in state.get("datasets") or []:
        if dataset.get("urn"):
            return str(dataset["urn"])
    return None
