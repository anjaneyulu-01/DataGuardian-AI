"""The agent's public interface.

`GovernanceAgent.analyze(question)` is the single entry point. Everything else
in this package is an implementation detail: callers never construct the
graph, touch `AgentState`, or import a node.

The graph is compiled once per agent instance rather than per request —
compilation walks and validates the whole topology, which is wasted work on
every call.
"""

from __future__ import annotations

import logging
import time

from app.agents.planner import Planner
from app.agents.risk_engine import RiskEngine
from app.agents.state import (
    AgentResult,
    AgentState,
    Intent,
    NodeStatus,
    RiskLevel,
    new_state,
)
from app.agents.workflow import build_graph
from app.llm.base import BaseLLM
from app.tools import DataHubToolkit

logger = logging.getLogger(__name__)

# Hard ceiling on one analysis. Below the typical HTTP client timeout, so a
# stuck run surfaces as our typed error rather than a dropped connection.
DEFAULT_TIMEOUT_SECONDS = 120.0


class GovernanceAgent:
    """Multi-step governance analysis over DataHub metadata."""

    def __init__(
        self,
        *,
        toolkit: DataHubToolkit,
        llm: BaseLLM,
        planner: Planner | None = None,
        risk_engine: RiskEngine | None = None,
    ) -> None:
        """
        Args:
            toolkit: Tool layer — the agent's only path to DataHub.
            llm: Provider for planning and reasoning.
            planner: Override, for tests wanting deterministic planning.
            risk_engine: Override, for tests wanting custom thresholds.
        """
        self._llm = llm
        self._graph = build_graph(
            toolkit=toolkit, llm=llm, planner=planner, risk_engine=risk_engine
        )

    async def analyze(self, question: str) -> AgentResult:
        """Run the graph and return a structured answer.

        Never raises for an ordinary failure. A tool outage, an LLM timeout,
        or missing metadata all yield a result with `degraded=True`, the
        errors listed, and whatever evidence was gathered — because a partial
        governance answer is useful and a stack trace is not.
        """
        started = time.perf_counter()
        state = new_state(question)

        logger.info("agent.run start question=%r", question[:120])

        try:
            # `ainvoke` is typed as returning a plain dict; at runtime it is
            # the merged AgentState, and `_to_result` reads it through
            # `.get()` so a missing key is never fatal.
            final: AgentState = await self._graph.ainvoke(state)  # type: ignore[assignment]
        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.exception("agent.run FAILED after %.0fms", duration_ms)
            return _failed_result(question, exc, duration_ms)

        duration_ms = (time.perf_counter() - started) * 1000
        result = _to_result(question, final, duration_ms)

        logger.info(
            "agent.run done intent=%s risk=%s/%d findings=%d nodes=%d %.0fms%s",
            result.intent.value,
            result.risk_level.value,
            result.risk_score,
            len(result.findings),
            len(result.trace),
            duration_ms,
            " DEGRADED" if result.degraded else "",
        )
        return result

    async def aclose(self) -> None:
        """Release the LLM provider's connection pool."""
        await self._llm.aclose()


def _to_result(question: str, state: AgentState, duration_ms: float) -> AgentResult:
    """Project the final state onto the response contract."""
    trace = state.get("trace") or []
    return AgentResult(
        question=question,
        intent=state.get("intent", Intent.UNKNOWN),
        summary=state.get("summary", "") or "No summary was produced.",
        risk_level=state.get("risk_level", RiskLevel.LOW),
        risk_score=state.get("risk_score", 0),
        findings=state.get("findings") or [],
        recommendations=state.get("recommendations") or [],
        evidence=state.get("evidence") or [],
        business_impact=state.get("business_impact", ""),
        next_steps=state.get("next_steps") or [],
        trace=trace,
        errors=state.get("errors") or [],
        degraded=bool(state.get("degraded")),
        duration_ms=duration_ms,
        llm_provider=state.get("llm_provider", ""),
        # Only nodes that genuinely ran — the honest answer to "what did it do?"
        tools_used=[t.node for t in trace if t.status is NodeStatus.OK],
    )


def _failed_result(question: str, exc: Exception, duration_ms: float) -> AgentResult:
    """Result for a graph-level failure.

    Reached only if LangGraph itself fails, since node errors are contained by
    `executor.run_node`. Still returns the contract rather than raising, so the
    API surface stays uniform.
    """
    detail = getattr(exc, "detail", None) or str(exc)
    return AgentResult(
        question=question,
        intent=Intent.UNKNOWN,
        summary=(
            f"The analysis could not be completed. {type(exc).__name__}: {detail}"
        ),
        risk_level=RiskLevel.LOW,
        risk_score=0,
        errors=[f"graph: {type(exc).__name__}: {detail}"],
        degraded=True,
        duration_ms=duration_ms,
    )
