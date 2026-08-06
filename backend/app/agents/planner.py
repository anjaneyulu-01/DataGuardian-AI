"""Intent classification and tool selection.

The planner decides two things before any tool runs:

1. **What is being asked** (`Intent`).
2. **Which nodes are needed** (`plan`).

Both matter. Calling every tool on every question would triple latency and
burn DataHub quota to fetch lineage nobody asked about — and "chooses its own
tools" is precisely what separates an agent from a chatbot with a search box.

Classification is **rules first, LLM second**:

* A deterministic keyword pass handles the common phrasings. It is instant,
  free, reproducible, and testable without a network.
* Only when that is genuinely uncertain does the planner ask the LLM, which
  is bounded to returning one of the known intent names.
* If the LLM is unavailable, the rule verdict stands. Planning never hard-
  fails on a provider outage.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.agents.state import Intent
from app.llm.base import BaseLLM
from app.llm.exceptions import LLMError

logger = logging.getLogger(__name__)

# Node names, kept as constants so the planner and the graph cannot disagree
# about spelling.
NODE_DATASETS = "datasets"
NODE_OWNERS = "owners"
NODE_LINEAGE = "lineage"
NODE_STATISTICS = "statistics"
NODE_RISK = "risk"
NODE_REASONING = "reasoning"
NODE_RECOMMENDATION = "recommendation"
NODE_REPORT = "report"


@dataclass(frozen=True)
class Plan:
    """The planner's decision."""

    intent: Intent
    #: Tool nodes to run, in graph order.
    nodes: list[str]
    reason: str
    target_urn: str | None = None
    target_name: str | None = None
    #: True when the LLM was consulted rather than rules alone.
    used_llm: bool = False


@dataclass(frozen=True)
class IntentRule:
    """Keyword signature for one intent."""

    intent: Intent
    #: Any of these present → strong signal.
    keywords: tuple[str, ...]
    #: All of these must also be absent, to break ties between similar asks.
    excludes: tuple[str, ...] = field(default=())
    weight: int = 1


# Ordered by specificity: narrower intents are checked before broader ones so
# "generate a governance report" is a REPORT, not ANALYZE_GOVERNANCE.
_RULES: tuple[IntentRule, ...] = (
    IntentRule(
        Intent.GENERATE_REPORT,
        ("report", "executive summary", "daily summary", "weekly summary", "briefing"),
        weight=3,
    ),
    IntentRule(
        Intent.GENERATE_DOCUMENTATION,
        ("documentation", "document", "readme", "data dictionary", "describe"),
        excludes=("report",),
        weight=3,
    ),
    IntentRule(
        Intent.FIND_MISSING_OWNERS,
        (
            "without owner",
            "no owner",
            "missing owner",
            "unowned",
            "who owns",
            "ownership",
        ),
        weight=3,
    ),
    IntentRule(
        Intent.ANALYZE_LINEAGE,
        ("lineage", "downstream", "upstream", "impact", "blast radius", "depends on"),
        weight=2,
    ),
    IntentRule(
        Intent.FIND_RISKY_DATASETS,
        ("risk", "risky", "dangerous", "critical", "vulnerable", "exposure", "pii"),
        weight=2,
    ),
    IntentRule(
        Intent.ANALYZE_GOVERNANCE,
        (
            "governance",
            "health",
            "compliance",
            "quality",
            "coverage",
            "analyze",
            "audit",
        ),
        weight=1,
    ),
)

# Which tools each intent needs. Everything funnels through risk → reasoning,
# because an answer without deterministic grounding is exactly what this
# product exists not to produce.
_INTENT_NODES: dict[Intent, list[str]] = {
    Intent.FIND_MISSING_OWNERS: [NODE_DATASETS, NODE_OWNERS, NODE_RISK, NODE_REASONING],
    Intent.ANALYZE_GOVERNANCE: [
        NODE_DATASETS,
        NODE_OWNERS,
        NODE_STATISTICS,
        NODE_RISK,
        NODE_REASONING,
    ],
    Intent.ANALYZE_LINEAGE: [NODE_DATASETS, NODE_LINEAGE, NODE_RISK, NODE_REASONING],
    Intent.FIND_RISKY_DATASETS: [
        NODE_DATASETS,
        NODE_OWNERS,
        NODE_LINEAGE,
        NODE_RISK,
        NODE_REASONING,
    ],
    Intent.GENERATE_DOCUMENTATION: [NODE_DATASETS, NODE_STATISTICS, NODE_REASONING],
    Intent.GENERATE_REPORT: [
        NODE_DATASETS,
        NODE_OWNERS,
        NODE_STATISTICS,
        NODE_RISK,
        NODE_REASONING,
        NODE_REPORT,
    ],
    # Still gathers a little context so the answer can explain what the agent
    # *can* do, grounded in the actual catalogue rather than a canned string.
    Intent.UNKNOWN: [NODE_DATASETS, NODE_REASONING],
}

# Intents that always end with a recommendation node.
_RECOMMEND_FOR = {
    Intent.FIND_MISSING_OWNERS,
    Intent.ANALYZE_GOVERNANCE,
    Intent.FIND_RISKY_DATASETS,
    Intent.ANALYZE_LINEAGE,
}

# A DataHub URN quoted anywhere in the question.
_URN_PATTERN = re.compile(r"urn:li:[a-zA-Z]+:\([^)]*\)|urn:li:[a-zA-Z]+:[\w.\-]+")

# A bare asset name: dotted path or snake_case identifier of reasonable length.
_NAME_PATTERN = re.compile(r"\b([a-z][a-z0-9_]{2,}(?:\.[a-z0-9_]+){0,3})\b")

# Words that look like identifiers but are ordinary English in this domain.
_NAME_STOPWORDS = frozenset(
    {
        "datasets",
        "dataset",
        "owners",
        "owner",
        "lineage",
        "governance",
        "documentation",
        "report",
        "risk",
        "risky",
        "without",
        "missing",
        "analyze",
        "analyse",
        "explain",
        "generate",
        "which",
        "what",
        "show",
        "find",
        "assets",
        "asset",
        "metadata",
        "downstream",
        "upstream",
        "impact",
        "summary",
        "health",
        "quality",
        "compliance",
        "coverage",
        "critical",
        "highest",
        "table",
        "tables",
        "have",
        "that",
        "with",
        "the",
        "and",
        "for",
        "are",
        "all",
        "any",
        "pii",
        "tags",
        "tag",
    }
)

_CLASSIFY_SYSTEM = (
    "You classify data-governance questions. Reply with EXACTLY ONE of these "
    "labels and nothing else: " + ", ".join(i.value for i in Intent) + "."
)


class Planner:
    """Classifies a question and selects the tools needed to answer it."""

    def __init__(self, llm: BaseLLM | None = None) -> None:
        """
        Args:
            llm: Used only to disambiguate questions the rules cannot classify.
                Omit it and the planner is fully deterministic.
        """
        self._llm = llm

    async def plan(self, question: str) -> Plan:
        """Classify `question` and choose the nodes to run."""
        text = (question or "").strip()
        if not text:
            return Plan(
                intent=Intent.UNKNOWN,
                nodes=_nodes_for(Intent.UNKNOWN),
                reason="Empty question.",
                used_llm=False,
            )

        intent, confident, reason = self._classify_by_rules(text)
        used_llm = False

        if not confident and self._llm is not None:
            llm_intent = await self._classify_by_llm(text)
            if llm_intent is not None:
                intent, used_llm = llm_intent, True
                reason = (
                    "Rules were inconclusive; the model classified it as "
                    f"{intent.value}."
                )

        target_urn, target_name = self._extract_target(text)

        return Plan(
            intent=intent,
            nodes=_nodes_for(intent, has_target=bool(target_urn or target_name)),
            reason=reason,
            target_urn=target_urn,
            target_name=target_name,
            used_llm=used_llm,
        )

    # -- Classification ---------------------------------------------------------------

    def _classify_by_rules(self, question: str) -> tuple[Intent, bool, str]:
        """Keyword scoring. Returns (intent, confident, human-readable reason)."""
        lowered = question.lower()
        scores: dict[Intent, int] = {}
        matched: dict[Intent, list[str]] = {}

        for rule in _RULES:
            if any(excluded in lowered for excluded in rule.excludes):
                continue
            hits = [kw for kw in rule.keywords if kw in lowered]
            if hits:
                scores[rule.intent] = scores.get(rule.intent, 0) + rule.weight * len(
                    hits
                )
                matched.setdefault(rule.intent, []).extend(hits)

        if not scores:
            return (
                Intent.UNKNOWN,
                False,
                "No governance keywords matched.",
            )

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        best, best_score = ranked[0]
        runner_up = ranked[1][1] if len(ranked) > 1 else 0

        # Confident when the winner is clear. A near-tie is exactly the case
        # worth spending an LLM call on.
        confident = best_score >= 2 and best_score > runner_up

        return (
            best,
            confident,
            f"Matched {', '.join(sorted(set(matched[best])))!r} → {best.value}.",
        )

    async def _classify_by_llm(self, question: str) -> Intent | None:
        """Ask the model to pick a label. Returns None if it cannot help.

        Never raises: planning must survive an LLM outage, falling back to the
        rule verdict.
        """
        if self._llm is None:
            return None
        try:
            response = await self._llm.generate(
                f"Question: {question}\n\nLabel:",
                system=_CLASSIFY_SYSTEM,
                temperature=0.0,
                max_tokens=800,
            )
        except LLMError as exc:
            logger.warning("Planner LLM classification unavailable: %s", exc.detail)
            return None

        answer = response.text.strip().lower()
        for intent in Intent:
            if intent.value in answer:
                return intent
        logger.info("Planner could not parse an intent from %r", answer[:80])
        return None

    # -- Target extraction ------------------------------------------------------------

    def _extract_target(self, question: str) -> tuple[str | None, str | None]:
        """Pull an explicit URN, or a probable asset name, out of the question.

        A named target switches the plan from "scan the catalogue" to
        "investigate this one asset", which is a large difference in cost.
        """
        urn_match = _URN_PATTERN.search(question)
        if urn_match:
            return urn_match.group(0), None

        for candidate in _NAME_PATTERN.findall(question.lower()):
            head = candidate.split(".")[0]
            if head in _NAME_STOPWORDS:
                continue
            # Require a table-ish shape: an underscore or a dotted path. Plain
            # English words rarely have either.
            if "_" in candidate or "." in candidate:
                return None, candidate
        return None, None


def _nodes_for(intent: Intent, *, has_target: bool = False) -> list[str]:
    """Nodes for an intent, plus conditional additions."""
    nodes = list(_INTENT_NODES.get(intent, _INTENT_NODES[Intent.UNKNOWN]))

    # A specifically named asset makes lineage worth fetching — blast radius is
    # the first thing anyone asks about a single table.
    if has_target and NODE_LINEAGE not in nodes and NODE_RISK in nodes:
        nodes.insert(nodes.index(NODE_RISK), NODE_LINEAGE)

    if intent in _RECOMMEND_FOR and NODE_RECOMMENDATION not in nodes:
        nodes.append(NODE_RECOMMENDATION)

    return nodes
