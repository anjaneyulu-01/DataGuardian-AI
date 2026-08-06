"""Report node — formats a governance report.

Runs only for `GENERATE_REPORT`. It does not gather anything new: by this
point the graph already holds the facts, the verdict, and the reasoning. Its
job is presentation — an executive-readable narrative built on the same
evidence, with no new claims introduced.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from app.agents.executor import NodeFn, run_node
from app.agents.state import AgentState, Finding
from app.llm.base import BaseLLM
from app.llm.exceptions import LLMError

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are DataGuardian, writing a governance report for data leadership. "
    "Use only the supplied evidence and verdict — introduce no new facts. "
    "Lead with the conclusion, quantify wherever the evidence allows, and "
    "keep it to what a busy executive will actually read."
)


class _Report(BaseModel):
    headline: str = Field(description="One-line verdict for the report title.")
    executive_summary: str = Field(
        description="3-5 sentences: posture, biggest risk, trend if known."
    )
    priorities: list[str] = Field(
        description="2-4 prioritised areas needing attention."
    )


def make_report_node(llm: BaseLLM) -> NodeFn:
    """Build the report node bound to an LLM provider."""

    async def report_node(state: AgentState) -> dict[str, Any]:
        async def body(current: AgentState) -> dict[str, Any]:
            findings: list[Finding] = current.get("findings") or []

            try:
                report = await llm.structured_output(
                    _prompt(current, findings), _Report, system=_SYSTEM
                )
                # Prepend the headline so the report reads as a report; the
                # reasoning node's summary becomes the body.
                summary = (
                    f"{report.headline.strip()}\n\n{report.executive_summary.strip()}"
                )
                existing_steps = current.get("next_steps") or []
                return {
                    "summary": summary,
                    "next_steps": [s.strip() for s in report.priorities if s.strip()]
                    or existing_steps,
                }

            except LLMError as exc:
                # The reasoning node already produced a usable summary; keep
                # it rather than replacing it with a worse one.
                logger.warning(
                    "Report formatting unavailable (%s): %s",
                    type(exc).__name__,
                    exc.detail,
                )
                return {
                    "degraded": True,
                    "errors": [f"report: {exc.detail}"],
                }

        return await run_node("report", state, body)

    return report_node


def _prompt(state: AgentState, findings: list[Finding]) -> str:
    by_severity: dict[str, int] = {}
    for finding in findings:
        key = str(finding.severity)
        by_severity[key] = by_severity.get(key, 0) + 1

    payload = {
        "assets_examined": len(state.get("datasets") or []),
        "risk_score": state.get("risk_score", 0),
        "risk_level": str(state.get("risk_level", "low")),
        "total_findings": len(findings),
        "findings_by_severity": by_severity,
        "top_findings": [
            {"title": f.title, "asset": f.asset_name, "severity": str(f.severity)}
            for f in sorted(findings, key=lambda f: f.points, reverse=True)[:8]
        ],
        "analysis": state.get("summary", ""),
        "recommendations": [r.action for r in (state.get("recommendations") or [])],
    }
    return (
        "Write a governance report from this scan:\n"
        f"{json.dumps(payload, indent=2, default=str)}"
    )
