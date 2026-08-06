"""Reasoning node — the only place the LLM interprets anything.

Receives the deterministic verdict plus the evidence that produced it, and
returns prose: an executive summary and a business-impact statement. It is
explicitly told the score and level rather than asked to compute them, so the
model cannot contradict the engine.

Degradation is first-class. If the LLM is unreachable or every provider is
rate-limited, this node writes a factual summary assembled from the findings
themselves and marks the run degraded. A governance answer without polish is
still useful; a 500 is not.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from app.agents.executor import NodeFn, run_node
from app.agents.state import AgentState, Finding, Intent
from app.llm.base import BaseLLM
from app.llm.exceptions import LLMError

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are DataGuardian, an autonomous metadata governance engineer. "
    "You explain governance findings that have ALREADY been computed by a "
    "deterministic rule engine.\n\n"
    "Rules you must follow:\n"
    "- Never invent findings, assets, owners, or numbers. Use only the "
    "evidence given.\n"
    "- Never dispute or recalculate the risk score or level; they are "
    "authoritative.\n"
    "- If evidence is missing, say so plainly rather than guessing.\n"
    "- Write for a data steward: direct, specific, no filler or hedging."
)


class _Reasoning(BaseModel):
    """Schema the model must fill. Constrains output to what the UI renders."""

    summary: str = Field(
        description="2-4 sentences stating what was found and why it matters."
    )
    business_impact: str = Field(
        description="1-3 sentences on the concrete consequence to the business."
    )


def make_reasoning_node(llm: BaseLLM) -> NodeFn:
    """Build the reasoning node bound to an LLM provider."""

    async def reasoning_node(state: AgentState) -> dict[str, Any]:
        async def body(current: AgentState) -> dict[str, Any]:
            payload = _payload(current)
            started = time.perf_counter()

            try:
                reasoning = await llm.structured_output(
                    _prompt(current, payload), _Reasoning, system=_SYSTEM
                )
                latency_ms = (time.perf_counter() - started) * 1000
                return {
                    "summary": reasoning.summary.strip(),
                    "business_impact": reasoning.business_impact.strip(),
                    "llm_provider": _provider_name(llm),
                    "llm_latency_ms": latency_ms,
                }

            except LLMError as exc:
                # Fall back to a factual, template-built summary. Marked
                # degraded so the caller knows the prose is not model-written.
                logger.warning(
                    "Reasoning unavailable (%s); using deterministic summary: %s",
                    type(exc).__name__,
                    exc.detail,
                )
                return {
                    **_fallback_summary(current),
                    "llm_provider": f"{_provider_name(llm)} (unavailable)",
                    "llm_latency_ms": (time.perf_counter() - started) * 1000,
                    "degraded": True,
                    "errors": [f"reasoning: {exc.detail}"],
                }

        return await run_node("reasoning", state, body)

    return reasoning_node


def _provider_name(llm: BaseLLM) -> str:
    """Which model actually answered.

    A fail-over chain reports itself as "fallback", which tells a reader
    nothing when they are trying to work out why an answer reads oddly.
    `active_provider` names the vendor that actually served the call.
    """
    return str(getattr(llm, "active_provider", llm.name))


def _payload(state: AgentState) -> dict[str, Any]:
    """The JSON handed to the model — evidence and verdict, nothing else."""
    findings: list[Finding] = state.get("findings") or []
    return {
        "question": state.get("question", ""),
        "intent": str(state.get("intent", Intent.UNKNOWN)),
        "risk_score": state.get("risk_score", 0),
        "risk_level": str(state.get("risk_level", "low")),
        "assets_examined": len(state.get("datasets") or []),
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
        "evidence": state.get("evidence") or [],
        "statistics": state.get("statistics") or {},
    }


def _prompt(state: AgentState, payload: dict[str, Any]) -> str:
    degraded_note = (
        "\n\nNOTE: some tools failed, so the evidence is incomplete. Say so in "
        "the summary rather than implying full coverage."
        if state.get("degraded")
        else ""
    )
    return (
        f"A governance scan answered this question:\n"
        f"{state.get('question', '')}\n\n"
        f"The rule engine produced this verdict and evidence:\n"
        f"{json.dumps(payload, indent=2, default=str)}\n\n"
        f"Explain it.{degraded_note}"
    )


def _fallback_summary(state: AgentState) -> dict[str, str]:
    """Deterministic prose, used when no provider can be reached.

    Assembled from the findings, so it is accurate — just not eloquent.
    """
    findings: list[Finding] = state.get("findings") or []
    asset_count = len(state.get("datasets") or [])
    level = str(state.get("risk_level", "low"))
    score = state.get("risk_score", 0)

    if not findings:
        return {
            "summary": (
                f"Examined {asset_count} asset(s) and found no rule violations. "
                f"Risk level {level} (score {score})."
            ),
            "business_impact": "No governance issues were detected in this scan.",
        }

    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.title] = counts.get(finding.title, 0) + 1
    breakdown = "; ".join(f"{title} ({n})" for title, n in counts.items())

    return {
        "summary": (
            f"Examined {asset_count} asset(s) and found {len(findings)} rule "
            f"violation(s): {breakdown}. Risk level {level} (score {score}). "
            "AI explanation was unavailable, so this summary is generated "
            "directly from the rule engine."
        ),
        "business_impact": (
            "Findings are listed below with the rule each one triggered. "
            "Review them directly — the narrative explanation could not be "
            "generated."
        ),
    }
