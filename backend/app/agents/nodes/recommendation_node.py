"""Recommendation node — turns findings into corrective actions.

Runs only for intents where an action is the point (missing owners, risk,
governance analysis). Documentation and report intents skip it: their output
IS the deliverable.

The model proposes actions, but the *set of problems* it may act on is fixed
by the risk engine. It cannot recommend fixing something that was never found.
When the LLM is unavailable, each finding maps to a deterministic action, so
the caller always receives something to do.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from app.agents.executor import NodeFn, run_node
from app.agents.state import AgentState, Finding, Recommendation, RiskLevel
from app.llm.base import BaseLLM
from app.llm.exceptions import LLMError

logger = logging.getLogger(__name__)

MAX_RECOMMENDATIONS = 5

_SYSTEM = (
    "You are DataGuardian, an autonomous metadata governance engineer. "
    "You propose corrective actions for findings a deterministic rule engine "
    "has already identified.\n\n"
    "Rules:\n"
    "- Every recommendation must address one of the supplied findings.\n"
    "- Never invent a problem that is not in the findings.\n"
    "- Be specific and actionable: name the asset and the concrete step.\n"
    "- Order by impact, most urgent first.\n"
    "- Also give short, concrete next steps a steward can take today."
)

# One deterministic action per rule, used when the LLM cannot be reached.
_FALLBACK_ACTIONS: dict[str, tuple[str, str]] = {
    "missing_owner": (
        "Assign an accountable owner",
        "Ownership is the prerequisite for every other governance control.",
    ),
    "missing_documentation": (
        "Generate and review a description",
        "Consumers cannot assess fitness for use without one.",
    ),
    "untagged_pii": (
        "Apply a PII classification tag",
        "Untagged personal data is a compliance exposure and blocks access control.",
    ),
    "large_downstream_impact": (
        "Add a freshness SLA and on-call ownership",
        "Blast radius this size means failures reach production consumers.",
    ),
    "deprecated_in_use": (
        "Migrate remaining consumers and set a decommission date",
        "Deprecated assets still in use silently serve stale data.",
    ),
    "schema_drift": (
        "Reconcile downstream models with the new schema",
        "Drift breaks consumers quietly, often without an error.",
    ),
}


class _Recommendation(BaseModel):
    action: str = Field(description="The concrete corrective step.")
    rationale: str = Field(description="One sentence on why it matters.")
    priority: str = Field(description="critical, high, medium, or low")
    asset_name: str | None = Field(default=None, description="Asset it applies to.")


class _Recommendations(BaseModel):
    recommendations: list[_Recommendation]
    next_steps: list[str] = Field(description="2-4 short imperative steps for today.")


def make_recommendation_node(llm: BaseLLM) -> NodeFn:
    """Build the recommendation node bound to an LLM provider."""

    async def recommendation_node(state: AgentState) -> dict[str, Any]:
        async def body(current: AgentState) -> dict[str, Any]:
            findings: list[Finding] = current.get("findings") or []
            if not findings:
                return {
                    "recommendations": [],
                    "next_steps": ["No action required — no violations were found."],
                }

            try:
                result = await llm.structured_output(
                    _prompt(current, findings), _Recommendations, system=_SYSTEM
                )
                return {
                    "recommendations": [
                        Recommendation(
                            action=r.action.strip(),
                            rationale=r.rationale.strip(),
                            priority=_coerce_priority(r.priority),
                            asset_urn=_urn_for(r.asset_name, findings),
                        )
                        for r in result.recommendations[:MAX_RECOMMENDATIONS]
                    ],
                    "next_steps": [
                        s.strip() for s in result.next_steps[:4] if s.strip()
                    ],
                }

            except LLMError as exc:
                logger.warning(
                    "Recommendations unavailable (%s); deriving from rules: %s",
                    type(exc).__name__,
                    exc.detail,
                )
                return {
                    **_fallback_recommendations(findings),
                    "degraded": True,
                    "errors": [f"recommendation: {exc.detail}"],
                }

        return await run_node("recommendation", state, body)

    return recommendation_node


def _prompt(state: AgentState, findings: list[Finding]) -> str:
    payload = {
        "question": state.get("question", ""),
        "risk_level": str(state.get("risk_level", "low")),
        "risk_score": state.get("risk_score", 0),
        "findings": [
            {
                "rule": f.rule,
                "title": f.title,
                "severity": str(f.severity),
                "asset": f.asset_name,
                "detail": f.detail,
            }
            for f in findings[:15]
        ],
    }
    return (
        "Propose corrective actions for these findings:\n"
        f"{json.dumps(payload, indent=2, default=str)}"
    )


def _coerce_priority(value: str) -> RiskLevel:
    """Map free-text priority onto the enum, defaulting rather than failing."""
    try:
        return RiskLevel(value.strip().lower())
    except ValueError:
        return RiskLevel.MEDIUM


def _urn_for(asset_name: str | None, findings: list[Finding]) -> str | None:
    """Resolve a model-supplied asset name back to a real URN.

    Only names that appear in the findings resolve, so a hallucinated asset
    name yields `None` rather than a fabricated URN.
    """
    if not asset_name:
        return None
    for finding in findings:
        if finding.asset_name and finding.asset_name.lower() == asset_name.lower():
            return finding.asset_urn
    return None


def _fallback_recommendations(findings: list[Finding]) -> dict[str, Any]:
    """One action per distinct rule, ordered by the points it carries."""
    seen: dict[str, Finding] = {}
    for finding in findings:
        if finding.rule not in seen:
            seen[finding.rule] = finding

    ranked = sorted(seen.values(), key=lambda f: f.points, reverse=True)
    recommendations = [
        Recommendation(
            action=f"{_FALLBACK_ACTIONS[f.rule][0]} for {f.asset_name}"
            if f.asset_name
            else _FALLBACK_ACTIONS[f.rule][0],
            rationale=_FALLBACK_ACTIONS[f.rule][1],
            priority=f.severity,
            asset_urn=f.asset_urn,
        )
        for f in ranked[:MAX_RECOMMENDATIONS]
        if f.rule in _FALLBACK_ACTIONS
    ]

    return {
        "recommendations": recommendations,
        "next_steps": [r.action for r in recommendations[:3]],
    }
