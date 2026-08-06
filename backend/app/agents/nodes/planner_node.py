"""Planner node — the graph's entry point."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.executor import NodeFn, run_node
from app.agents.planner import Planner
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def make_planner_node(planner: Planner) -> NodeFn:
    """Build the planner node bound to a `Planner`.

    Nodes are factories rather than plain functions so their dependencies are
    injected once at graph-build time. LangGraph calls them with state only.
    """

    async def planner_node(state: AgentState) -> dict[str, Any]:
        async def body(current: AgentState) -> dict[str, Any]:
            plan = await planner.plan(current.get("question", ""))
            logger.info(
                "agent.plan intent=%s nodes=%s llm=%s",
                plan.intent.value,
                plan.nodes,
                plan.used_llm,
            )
            return {
                "intent": plan.intent,
                "plan": plan.nodes,
                "plan_reason": plan.reason,
                "target_urn": plan.target_urn,
                "target_name": plan.target_name,
            }

        return await run_node("planner", state, body)

    return planner_node
