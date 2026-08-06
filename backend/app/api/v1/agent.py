"""Agent endpoint.

One route: ask a governance question, get a structured answer. The router
stays thin — it validates input, calls `GovernanceAgent.analyze`, and returns
the result. All orchestration lives in the graph.

Always HTTP 200 for a completed run, including degraded ones. A partial
answer is a *result*, not a transport failure: the caller reads `degraded`
and `errors` to see what was missing. Reserving non-2xx for genuine request
problems keeps the contract honest.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.state import AgentResult
from app.api.deps import GovernanceAgentDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


class AnalyzeRequest(BaseModel):
    """Input to the agent."""

    question: str = Field(
        min_length=3,
        max_length=1000,
        description="A governance question in plain language.",
        examples=["Find datasets without owners."],
    )


@router.post(
    "/analyze",
    response_model=AgentResult,
    summary="Run a governance analysis",
    response_description=(
        "Structured analysis: summary, risk score and level, findings, "
        "recommendations, evidence, and the execution trace."
    ),
)
async def analyze(request: AnalyzeRequest, agent: GovernanceAgentDep) -> AgentResult:
    """Plan, gather evidence, score risk, and explain the result.

    The agent chooses which tools to run from the question, so a narrow ask
    ("who owns X?") costs far less than a broad one ("audit the catalogue").

    `findings`, `risk_score`, and `risk_level` come from the deterministic
    rule engine and are reproducible. `summary`, `business_impact`,
    `recommendations`, and `next_steps` are model-generated, constrained to
    the findings. `trace` shows exactly which nodes ran and how long each took.
    """
    return await agent.analyze(request.question)
