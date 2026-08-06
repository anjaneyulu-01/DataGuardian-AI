"""Risk node — the deterministic verdict.

Runs `RiskEngine` over the gathered facts. No LLM call happens here, and none
may be added: this node is the reason the agent's numbers are reproducible.

It also builds the `evidence` list — the compact, factual payload the
reasoning node hands to the model. Evidence is assembled here rather than in
the reasoning node so that what the LLM sees is always exactly what was
scored.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.executor import NodeFn, run_node
from app.agents.risk_engine import RiskEngine
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# Assets included in the evidence payload. The score considers every asset;
# this caps only what is described to the model.
MAX_EVIDENCE_ASSETS = 10


def make_risk_node(engine: RiskEngine) -> NodeFn:
    """Build the risk node bound to a `RiskEngine`."""

    async def risk_node(state: AgentState) -> dict[str, Any]:
        async def body(current: AgentState) -> dict[str, Any]:
            datasets = current.get("datasets") or []
            lineage = current.get("lineage") or {}
            statistics = current.get("statistics") or {}

            if not datasets:
                # Nothing to score. An honest zero, not a guess.
                return {
                    "risk_score": 0,
                    "risk_level": engine.assess_many([]).level,
                    "findings": [],
                    "evidence": [],
                }

            if len(datasets) == 1:
                assessment = engine.assess_dataset(
                    datasets[0], lineage=lineage, statistics=statistics
                )
            else:
                assessment = engine.assess_many(datasets, lineage=lineage)

            logger.info(
                "agent.risk score=%d level=%s rules=%s",
                assessment.score,
                assessment.level.value,
                sorted(set(assessment.triggered_rules)),
            )

            return {
                "risk_score": assessment.score,
                "risk_level": assessment.level,
                "findings": assessment.findings,
                "evidence": _build_evidence(datasets, current, assessment.findings),
            }

        return await run_node("risk", state, body)

    return risk_node


def _build_evidence(
    datasets: list[dict[str, Any]],
    state: AgentState,
    findings: list[Any],
) -> list[dict[str, Any]]:
    """Compact, factual payload for the LLM.

    Deliberately narrow: only the fields a governance explanation needs. A
    full serialised dataset carries schema, custom properties, and timestamps
    that inflate the prompt without improving the answer.
    """
    findings_by_urn: dict[str, list[str]] = {}
    for finding in findings:
        urn = getattr(finding, "asset_urn", None)
        if urn:
            findings_by_urn.setdefault(urn, []).append(finding.rule)

    lineage = state.get("lineage") or {}
    root_urn = lineage.get("root_urn")

    evidence: list[dict[str, Any]] = []
    for dataset in datasets[:MAX_EVIDENCE_ASSETS]:
        urn = str(dataset.get("urn") or "")
        platform = dataset.get("platform") or {}
        entry: dict[str, Any] = {
            "name": dataset.get("name"),
            "urn": urn,
            "platform": platform.get("name") if isinstance(platform, dict) else None,
            "owners": [
                owner.get("display_name") or owner.get("name")
                for owner in (dataset.get("owners") or [])
            ],
            "has_description": bool((dataset.get("description") or "").strip()),
            "tags": [
                tag.get("name")
                for tag in (dataset.get("tags") or [])
                if isinstance(tag, dict)
            ],
            "triggered_rules": findings_by_urn.get(urn, []),
        }

        domain = dataset.get("domain")
        if isinstance(domain, dict) and domain.get("name"):
            entry["domain"] = domain["name"]

        # Attach lineage only to the asset it was actually traced from.
        if root_urn and urn == root_urn:
            entry["downstream_count"] = (lineage.get("downstream") or {}).get(
                "total", 0
            )
            entry["upstream_count"] = (lineage.get("upstream") or {}).get("total", 0)

        evidence.append(entry)

    return evidence
