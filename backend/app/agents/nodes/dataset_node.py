"""Dataset node — fetches the assets the question is about.

Consumes `DatasetTool` only. Neither this node nor any other in the graph
holds a DataHub client, which is what keeps the "AI never touches DataHub
directly" boundary structural rather than a convention.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.executor import NodeFn, run_node
from app.agents.state import AgentState, Intent
from app.tools import DataHubToolkit
from app.tools.base import DataHubTool

logger = logging.getLogger(__name__)

# How many assets a catalogue-wide scan pulls. Bounded because the evidence
# eventually goes into a prompt, and an unbounded page would blow the context
# window and the token bill.
SCAN_PAGE_SIZE = 25


def make_dataset_node(tools: DataHubToolkit) -> NodeFn:
    """Build the dataset node bound to a toolkit."""

    async def dataset_node(state: AgentState) -> dict[str, Any]:
        async def body(current: AgentState) -> dict[str, Any]:
            urn = current.get("target_urn")
            name = current.get("target_name")
            intent = current.get("intent", Intent.UNKNOWN)

            # A named URN → one precise lookup instead of a catalogue scan.
            if urn:
                dataset = await tools.datasets.get(urn)
                return {"datasets": [DataHubTool.serialize(dataset)]}

            # A probable asset name → search for it, but fall back to a scan
            # if the guess matched nothing. A bad name guess must not produce
            # an empty, confidently wrong answer.
            if name:
                page = await tools.datasets.search(name, count=SCAN_PAGE_SIZE)
                if page.results:
                    return {"datasets": DataHubTool.serialize(page.results)}
                logger.info(
                    "Target %r matched no assets; falling back to a catalogue scan",
                    name,
                )

            page = await tools.datasets.list(count=SCAN_PAGE_SIZE)
            datasets = DataHubTool.serialize(page.results)

            # For owner-focused questions, lead with the assets that actually
            # lack owners so the evidence sent to the LLM is the relevant slice.
            if intent is Intent.FIND_MISSING_OWNERS:
                datasets.sort(key=lambda d: bool(d.get("owners")))

            return {"datasets": datasets}

        return await run_node("datasets", state, body)

    return dataset_node
