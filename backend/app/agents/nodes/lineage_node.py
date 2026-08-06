"""Lineage node — establishes blast radius.

Lineage is what turns a finding into a priority: untagged PII in a table
feeding three executive dashboards is a different problem from the same issue
in an orphaned scratch table. The risk engine reads the downstream count this
node produces.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.executor import NodeFn, run_node
from app.agents.state import AgentState
from app.tools import DataHubToolkit
from app.tools.base import DataHubTool

logger = logging.getLogger(__name__)

# Nodes returned per direction. Enough to judge blast radius without
# flooding the prompt.
LINEAGE_PAGE_SIZE = 20


def make_lineage_node(tools: DataHubToolkit) -> NodeFn:
    """Build the lineage node bound to a toolkit."""

    async def lineage_node(state: AgentState) -> dict[str, Any]:
        async def body(current: AgentState) -> dict[str, Any]:
            urn = current.get("target_urn") or _first_dataset_urn(current)
            if not urn:
                # No asset in scope. Not an error — a catalogue-wide question
                # legitimately has no single lineage root.
                return {"lineage": {}}

            impact = await tools.lineage.impact(urn, count=LINEAGE_PAGE_SIZE)
            serialised = DataHubTool.serialize(impact)

            upstream = serialised.get("upstream", {}).get("total", 0)
            downstream = serialised.get("downstream", {}).get("total", 0)
            logger.info(
                "agent.lineage urn=%s upstream=%d downstream=%d",
                urn,
                upstream,
                downstream,
            )
            return {"lineage": {**serialised, "root_urn": urn}}

        return await run_node("lineage", state, body)

    return lineage_node


def _first_dataset_urn(state: AgentState) -> str | None:
    """Highest-signal asset to trace from.

    When no asset was named, trace the one most likely to matter: the first
    unowned asset if there is one, else simply the first. Tracing an arbitrary
    asset would produce lineage the answer never references.
    """
    datasets = state.get("datasets") or []
    for dataset in datasets:
        if not dataset.get("owners") and dataset.get("urn"):
            return str(dataset["urn"])
    for dataset in datasets:
        if dataset.get("urn"):
            return str(dataset["urn"])
    return None
