"""Deterministic governance scoring.

This module decides what is wrong and how bad it is. The LLM never does —
it only explains what this file already concluded.

That split is the product's central claim to trustworthiness:

* **Reproducible.** The same metadata always scores identically. A steward can
  re-run a scan and get the same number, which is impossible with a sampled
  language model.
* **Auditable.** Every point in the score traces to a named rule, so a
  disputed finding can be checked by hand.
* **Cheap.** Scoring 400 assets costs no tokens and no network round-trip.
* **Safe.** An LLM asked to score risk will confidently invent violations
  that are not in the data. Rules cannot.

Rule weights are policy, not physics — they encode a judgement about what
matters and are meant to be tuned. They live in `RULES` so that tuning is a
one-line change with a test, rather than an edit scattered across nodes.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from app.agents.state import Finding, RiskLevel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Rule:
    """One governance rule and the weight it contributes."""

    key: str
    title: str
    points: int
    severity: RiskLevel


# The rule book. Weights reflect blast radius and regulatory exposure:
# untagged PII outranks everything because it is the only rule with a
# compliance consequence, while a missing description is a productivity cost.
RULES: dict[str, Rule] = {
    "untagged_pii": Rule(
        key="untagged_pii",
        title="Probable PII without a classification tag",
        points=40,
        severity=RiskLevel.CRITICAL,
    ),
    "missing_owner": Rule(
        key="missing_owner",
        title="No owner assigned",
        points=30,
        severity=RiskLevel.HIGH,
    ),
    "missing_documentation": Rule(
        key="missing_documentation",
        title="No description or documentation",
        points=20,
        severity=RiskLevel.MEDIUM,
    ),
    "large_downstream_impact": Rule(
        key="large_downstream_impact",
        title="Large downstream blast radius",
        points=20,
        severity=RiskLevel.HIGH,
    ),
    "deprecated_in_use": Rule(
        key="deprecated_in_use",
        title="Deprecated but still consumed",
        points=15,
        severity=RiskLevel.HIGH,
    ),
    "schema_drift": Rule(
        key="schema_drift",
        title="Schema drift since last scan",
        points=15,
        severity=RiskLevel.MEDIUM,
    ),
}

# Score bands. A single critical rule (untagged PII, 40) lands in HIGH on its
# own; CRITICAL requires a compounding failure, which is what actually
# warrants waking someone up.
_BANDS: Sequence[tuple[int, RiskLevel]] = (
    (70, RiskLevel.CRITICAL),
    (40, RiskLevel.HIGH),
    (20, RiskLevel.MEDIUM),
)

# Downstream consumers before blast radius counts as a risk multiplier.
DOWNSTREAM_THRESHOLD = 5

# Column-name patterns that suggest personal data. Deliberately conservative:
# a false positive costs a steward thirty seconds, a false negative is a
# compliance incident. Word-boundary anchored so `email` does not match
# `emailer_job_id`.
_PII_PATTERNS = re.compile(
    r"(?:^|_)(?:"
    # Contact details.
    r"email|phone|mobile|address|postcode|zip_?code"
    # Government and financial identifiers.
    r"|ssn|sin|nin|passport|tax_?id|national_?id"
    r"|credit_?card|card_?number|iban|account_?number"
    # Names.
    r"|first_?name|last_?name|full_?name|sur_?name|maiden_?name"
    # Dates of birth. `date_of_birth` needs its own alternative: the
    # surrounding (?:^|_) and (?:_|$) anchors match single tokens, so a
    # three-word column would otherwise slip through.
    r"|dob|birth_?date|date_of_birth|birth_?day"
    r")(?:_|$)",
    re.IGNORECASE,
)

# Tags that count as a PII classification already being present.
_PII_TAG_HINTS = ("pii", "sensitive", "personal", "gdpr", "confidential", "phi")


def looks_like_pii(field_path: str) -> bool:
    """Whether a column name suggests personal data."""
    return bool(_PII_PATTERNS.search(field_path))


def has_pii_tag(tags: Iterable[str]) -> bool:
    """Whether any tag already classifies the asset as sensitive."""
    return any(hint in tag.lower() for tag in tags for hint in _PII_TAG_HINTS)


def score_to_level(score: int) -> RiskLevel:
    """Map a numeric score onto its band."""
    for threshold, level in _BANDS:
        if score >= threshold:
            return level
    return RiskLevel.LOW


@dataclass(frozen=True)
class RiskAssessment:
    """The engine's verdict for one asset or for a whole scan."""

    score: int
    level: RiskLevel
    findings: list[Finding]

    @property
    def triggered_rules(self) -> list[str]:
        return [f.rule for f in self.findings]


class RiskEngine:
    """Applies `RULES` to Tool-layer output.

    Stateless and synchronous by design: no I/O, no LLM, no clock. That makes
    it trivially testable and safe to run over hundreds of assets inside a
    single node.
    """

    def __init__(self, downstream_threshold: int = DOWNSTREAM_THRESHOLD) -> None:
        self._downstream_threshold = downstream_threshold

    # -- Public API ---------------------------------------------------------------

    def assess_dataset(
        self,
        dataset: dict[str, Any],
        *,
        lineage: dict[str, Any] | None = None,
        statistics: dict[str, Any] | None = None,
    ) -> RiskAssessment:
        """Score one dataset.

        Args:
            dataset: A serialised `DatasetSummary` or `Dataset` from the Tool
                layer.
            lineage: Optional serialised `Lineage`, for blast radius.
            statistics: Optional statistics summary, currently used only to
                distinguish "no profile" from "profiled and empty".

        Returns:
            The score, its band, and one `Finding` per triggered rule.
        """
        urn = str(dataset.get("urn") or "")
        name = str(dataset.get("name") or urn.rsplit(",", 2)[-2:-1] or "unknown")
        findings: list[Finding] = []

        if not dataset.get("owners"):
            findings.append(
                self._finding(
                    "missing_owner",
                    urn,
                    name,
                    "No owner is assigned, so there is no accountable "
                    "responder when this asset breaks.",
                )
            )

        if not (dataset.get("description") or "").strip():
            findings.append(
                self._finding(
                    "missing_documentation",
                    urn,
                    name,
                    "No description, so consumers cannot tell what this asset "
                    "means or whether it fits their use case.",
                )
            )

        pii_columns = self._untagged_pii_columns(dataset)
        if pii_columns:
            shown = ", ".join(pii_columns[:5])
            more = f" (+{len(pii_columns) - 5} more)" if len(pii_columns) > 5 else ""
            findings.append(
                self._finding(
                    "untagged_pii",
                    urn,
                    name,
                    f"Columns match personal-data patterns but carry no "
                    f"classification tag: {shown}{more}.",
                )
            )

        downstream = self._downstream_count(dataset, lineage)
        if downstream >= self._downstream_threshold:
            findings.append(
                self._finding(
                    "large_downstream_impact",
                    urn,
                    name,
                    f"{downstream} downstream assets consume this, so any "
                    "defect propagates widely.",
                )
            )

        deprecation = dataset.get("deprecation") or {}
        # Deprecated AND still consumed. A deprecated asset with no consumers
        # is a tidy retirement, not a finding.
        if (
            isinstance(deprecation, dict)
            and deprecation.get("deprecated")
            and downstream > 0
        ):
            findings.append(
                self._finding(
                    "deprecated_in_use",
                    urn,
                    name,
                    f"Marked deprecated but still read by {downstream} "
                    "asset(s), risking silently stale data.",
                )
            )

        if self._has_schema_drift(dataset, statistics):
            findings.append(
                self._finding(
                    "schema_drift",
                    urn,
                    name,
                    "Schema changed since the previous scan; downstream "
                    "models may not have been updated.",
                )
            )

        return self._assemble(findings)

    def assess_many(
        self,
        datasets: Sequence[dict[str, Any]],
        *,
        lineage: dict[str, Any] | None = None,
    ) -> RiskAssessment:
        """Score a set of datasets as one catalogue-level verdict.

        The score is the WORST asset's score, not the sum. Summing would make
        a catalogue of a thousand tidy assets look worse than one containing a
        single unowned PII table, which inverts the priority a steward needs.
        """
        all_findings: list[Finding] = []
        worst = 0

        for dataset in datasets:
            assessment = self.assess_dataset(dataset, lineage=lineage)
            all_findings.extend(assessment.findings)
            worst = max(worst, assessment.score)

        return RiskAssessment(
            score=worst, level=score_to_level(worst), findings=all_findings
        )

    # -- Rule helpers ---------------------------------------------------------------

    def _untagged_pii_columns(self, dataset: dict[str, Any]) -> list[str]:
        """Columns that look like PII on an asset with no sensitivity tag."""
        tags = [
            str(tag.get("name", "")) if isinstance(tag, dict) else str(tag)
            for tag in (dataset.get("tags") or [])
        ]
        if has_pii_tag(tags):
            return []

        schema = dataset.get("schema_metadata") or {}
        fields = schema.get("fields") or [] if isinstance(schema, dict) else []
        return [
            str(field.get("field_path"))
            for field in fields
            if isinstance(field, dict)
            and field.get("field_path")
            and looks_like_pii(str(field["field_path"]))
        ]

    def _downstream_count(
        self, dataset: dict[str, Any], lineage: dict[str, Any] | None
    ) -> int:
        """Consumer count, preferring live lineage over the dataset's own hint."""
        if lineage:
            downstream = lineage.get("downstream")
            if isinstance(downstream, dict):
                total = downstream.get("total")
                if isinstance(total, int):
                    return total
            total = lineage.get("total")
            if isinstance(total, int) and lineage.get("direction") == "DOWNSTREAM":
                return total

        hint = dataset.get("downstream_count")
        return hint if isinstance(hint, int) else 0

    def _has_schema_drift(
        self, dataset: dict[str, Any], statistics: dict[str, Any] | None
    ) -> bool:
        """Whether the schema changed since the last observation.

        TODO(agent): Real drift detection needs a stored snapshot of the
        previous schema, which arrives with the PostgreSQL scan-history model
        in Phase 3. Until then this fires only on an explicit upstream signal,
        and never guesses — a fabricated drift finding would be worse than a
        missed one.
        """
        explicit = dataset.get("schema_drift")
        if isinstance(explicit, bool):
            return explicit
        if statistics and isinstance(statistics.get("schema_drift"), bool):
            return bool(statistics["schema_drift"])
        return False

    # -- Assembly -------------------------------------------------------------------

    def _finding(self, rule_key: str, urn: str, name: str, detail: str) -> Finding:
        rule = RULES[rule_key]
        return Finding(
            rule=rule.key,
            title=rule.title,
            severity=rule.severity,
            points=rule.points,
            asset_urn=urn or None,
            asset_name=name,
            detail=detail,
        )

    def _assemble(self, findings: list[Finding]) -> RiskAssessment:
        """Total the points and derive the band.

        Capped at 100 so the score reads as a percentage-like figure; the
        individual findings still show the uncapped detail.
        """
        score = min(100, sum(f.points for f in findings))
        return RiskAssessment(
            score=score, level=score_to_level(score), findings=findings
        )
