"""Owner node — resolves accountability for the assets in scope."""

from __future__ import annotations

from typing import Any

from app.agents.executor import NodeFn, run_node
from app.agents.state import AgentState
from app.tools import DataHubToolkit
from app.tools.base import DataHubTool

# Per-asset owner lookups are one round-trip each, so a catalogue scan uses
# the aggregation instead. This bound only applies to the targeted path.
MAX_PER_ASSET_LOOKUPS = 10


def make_owner_node(tools: DataHubToolkit) -> NodeFn:
    """Build the owner node bound to a toolkit."""

    async def owner_node(state: AgentState) -> dict[str, Any]:
        async def body(current: AgentState) -> dict[str, Any]:
            urn = current.get("target_urn")

            # Single named asset → exactly its owners.
            if urn:
                owners = await tools.owners.for_dataset(urn)
                return {"owners": DataHubTool.serialize(owners)}

            # Catalogue-wide → one facet aggregation rather than N lookups.
            # `asset_count` comes back populated in this mode, which is what
            # makes "who owns the most unowned-adjacent assets" answerable.
            owners = await tools.owners.list()
            return {"owners": DataHubTool.serialize(owners)}

        return await run_node("owners", state, body)

    return owner_node
