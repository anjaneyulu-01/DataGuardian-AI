"""The autonomous governance agent.

A multi-step reasoning agent, not a chatbot: it plans which tools to use,
gathers evidence from the Tool layer, scores risk deterministically, and only
then asks an LLM to explain what was found.

Layering, outermost to innermost:

    governance_agent.py  Public interface — `GovernanceAgent.analyze()`
    workflow.py          LangGraph topology and conditional routing
    nodes/               One node per step, each dependency-injected
    planner.py           Intent classification and tool selection
    risk_engine.py       Deterministic governance rules — never the LLM
    executor.py          Timing, logging, failure containment per node
    state.py             The typed state threaded through the graph

The load-bearing rule: **the LLM never decides facts.** Which assets exist,
who owns them, what the lineage is, and how risky something is are all
determined by tools and rules. The model explains, summarises, and
recommends — nothing more.
"""

from app.agents.governance_agent import GovernanceAgent
from app.agents.planner import Plan, Planner
from app.agents.risk_engine import RULES, RiskAssessment, RiskEngine
from app.agents.state import (
    AgentResult,
    AgentState,
    Finding,
    Intent,
    NodeStatus,
    Recommendation,
    RiskLevel,
    TraceEntry,
)
from app.agents.workflow import build_graph

__all__ = [
    "RULES",
    "AgentResult",
    "AgentState",
    "Finding",
    "GovernanceAgent",
    "Intent",
    "NodeStatus",
    "Plan",
    "Planner",
    "Recommendation",
    "RiskAssessment",
    "RiskEngine",
    "RiskLevel",
    "TraceEntry",
    "build_graph",
]
