"""The LangGraph state machine.

Topology:

    START → planner ─┬→ datasets ─┬→ owners ─┬→ lineage ─┬→ statistics ─┐
                     │            │          │           │             │
                     └────────────┴──────────┴───────────┴─────────────┤
                                                                       ▼
                                                                     risk
                                                                       │
                                                                       ▼
                                                                   reasoning
                                                                       │
                                                             ┌─────────┴────────┐
                                                             ▼                  ▼
                                                      recommendation         report
                                                             │                  │
                                                             └────────→ END ◄───┘

Every edge between tool nodes is **conditional**. After each node the router
consults `state["plan"]` — written by the planner — and jumps to the next node
the plan actually asks for, skipping the rest. Asking "find datasets without
owners" therefore never fetches lineage or statistics.

Why a graph rather than a chain of `await` calls: the routing lives in data
(`plan`) instead of control flow, so adding an intent means editing a mapping,
not rewriting the pipeline. It also gives a uniform place to record the trace,
and leaves room for the loops and human-in-the-loop interrupts the roadmap
needs later.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.executor import NodeFn
from app.agents.nodes import (
    make_dataset_node,
    make_lineage_node,
    make_owner_node,
    make_planner_node,
    make_reasoning_node,
    make_recommendation_node,
    make_report_node,
    make_risk_node,
    make_statistics_node,
)
from app.agents.planner import (
    NODE_DATASETS,
    NODE_LINEAGE,
    NODE_OWNERS,
    NODE_REASONING,
    NODE_RECOMMENDATION,
    NODE_REPORT,
    NODE_RISK,
    NODE_STATISTICS,
    Planner,
)
from app.agents.risk_engine import RiskEngine
from app.agents.state import AgentState
from app.llm.base import BaseLLM
from app.tools import DataHubToolkit

logger = logging.getLogger(__name__)

NODE_PLANNER = "planner"

# The order nodes may run in. The router walks this list to find the next
# node the plan contains, which is what makes skipping possible without
# encoding every combination as an edge.
_PIPELINE: tuple[str, ...] = (
    NODE_DATASETS,
    NODE_OWNERS,
    NODE_LINEAGE,
    NODE_STATISTICS,
    NODE_RISK,
    NODE_REASONING,
    NODE_RECOMMENDATION,
    NODE_REPORT,
)


def _next_node(state: AgentState, after: str | None) -> str:
    """The next planned node after `after`, or END.

    `after=None` means "we just left the planner", so the search starts at the
    beginning of the pipeline.
    """
    plan = state.get("plan") or []
    start_index = 0 if after is None else _PIPELINE.index(after) + 1

    for candidate in _PIPELINE[start_index:]:
        if candidate in plan:
            return candidate
    return END


def build_graph(
    *,
    toolkit: DataHubToolkit,
    llm: BaseLLM,
    planner: Planner | None = None,
    risk_engine: RiskEngine | None = None,
) -> CompiledStateGraph:
    """Compile the governance graph.

    Args:
        toolkit: Tool layer — the agent's only route to DataHub.
        llm: Provider used by the planner and the three reasoning nodes.
        planner: Override for testing; defaults to an LLM-assisted planner.
        risk_engine: Override for testing; defaults to the standard rule book.

    Returns:
        A compiled graph. `ainvoke(state)` runs it.
    """
    resolved_planner = planner or Planner(llm=llm)
    resolved_engine = risk_engine or RiskEngine()

    graph: StateGraph = StateGraph(AgentState)

    for name, node_fn in (
        (NODE_PLANNER, make_planner_node(resolved_planner)),
        (NODE_DATASETS, make_dataset_node(toolkit)),
        (NODE_OWNERS, make_owner_node(toolkit)),
        (NODE_LINEAGE, make_lineage_node(toolkit)),
        (NODE_STATISTICS, make_statistics_node(toolkit)),
        (NODE_RISK, make_risk_node(resolved_engine)),
        (NODE_REASONING, make_reasoning_node(llm)),
        (NODE_RECOMMENDATION, make_recommendation_node(llm)),
        (NODE_REPORT, make_report_node(llm)),
    ):
        _add_node(graph, name, node_fn)

    graph.add_edge(START, NODE_PLANNER)

    # Every hop is a plan lookup. `_targets_after` lists the nodes reachable
    # from each point so LangGraph can validate the graph statically.
    graph.add_conditional_edges(
        NODE_PLANNER,
        _make_router(None),
        _targets_after(None),
    )
    for node in _PIPELINE:
        graph.add_conditional_edges(
            node,
            _make_router(node),
            _targets_after(node),
        )

    compiled = graph.compile()
    logger.info(
        "Governance graph compiled: %d nodes, conditional routing on `plan`",
        len(_PIPELINE) + 1,
    )
    return compiled


def _add_node(graph: StateGraph, name: str, node_fn: NodeFn) -> None:
    """Register a node.

    The single `type: ignore` in this module. LangGraph's `add_node` overloads
    do not model an async callable that takes a TypedDict and returns a
    *partial* update of it, which is exactly the shape every node here has and
    exactly what LangGraph supports at runtime. Confining the suppression to
    one helper keeps the other nine call sites honestly typed.
    """
    graph.add_node(name, node_fn)  # type: ignore[call-overload]


def _make_router(after: str | None) -> Callable[[AgentState], str]:
    """Router for the edges leaving `after` (or the planner, when None)."""

    def route(state: AgentState) -> str:
        destination = _next_node(state, after)
        logger.debug("agent.route %s → %s", after or NODE_PLANNER, destination)
        return destination

    return route


def _targets_after(after: str | None) -> list[str]:
    """Every node reachable from `after`, plus END."""
    start_index = 0 if after is None else _PIPELINE.index(after) + 1
    return [*_PIPELINE[start_index:], END]
