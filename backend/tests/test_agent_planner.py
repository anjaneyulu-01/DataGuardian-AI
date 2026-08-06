"""Planner tests.

Tool selection is what makes this an agent rather than a pipeline, so these
tests assert both halves: the intent, and the specific tools chosen for it.
"""

import pytest

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
from app.agents.state import Intent
from app.llm.exceptions import LLMTimeoutError
from tests.agent_doubles import StubLLM


class TestIntentClassification:
    @pytest.mark.parametrize(
        "question,expected",
        [
            ("Find datasets without owners", Intent.FIND_MISSING_OWNERS),
            ("Which assets are unowned?", Intent.FIND_MISSING_OWNERS),
            ("who owns fct_payments", Intent.FIND_MISSING_OWNERS),
            ("Show downstream impact of dim_customer", Intent.ANALYZE_LINEAGE),
            ("Explain the lineage", Intent.ANALYZE_LINEAGE),
            ("Which datasets are highest risk?", Intent.FIND_RISKY_DATASETS),
            ("Find untagged PII", Intent.FIND_RISKY_DATASETS),
            ("Generate documentation for stg_orders", Intent.GENERATE_DOCUMENTATION),
            ("Write a README", Intent.GENERATE_DOCUMENTATION),
            ("Create a governance report", Intent.GENERATE_REPORT),
            ("Give me an executive summary", Intent.GENERATE_REPORT),
            ("Analyze governance health", Intent.ANALYZE_GOVERNANCE),
        ],
    )
    async def test_rules_classify_common_phrasings(
        self, question: str, expected: Intent
    ) -> None:
        # No LLM: classification of the common cases must be free and instant.
        plan = await Planner().plan(question)
        assert plan.intent is expected
        assert plan.used_llm is False

    async def test_report_beats_governance_on_overlap(self) -> None:
        # "governance report" contains both signatures; the more specific
        # intent must win or every report becomes a plain analysis.
        plan = await Planner().plan("Create a governance report for this week")
        assert plan.intent is Intent.GENERATE_REPORT

    async def test_empty_question_is_unknown(self) -> None:
        plan = await Planner().plan("   ")
        assert plan.intent is Intent.UNKNOWN

    async def test_unmatched_question_without_llm_is_unknown(self) -> None:
        plan = await Planner().plan("What is the weather in Paris?")
        assert plan.intent is Intent.UNKNOWN


class TestLLMAssistedClassification:
    async def test_llm_resolves_what_rules_cannot(self) -> None:
        llm = StubLLM(reply="find_risky_datasets")
        plan = await Planner(llm=llm).plan("Anything I should worry about?")

        assert plan.intent is Intent.FIND_RISKY_DATASETS
        assert plan.used_llm is True
        assert llm.calls == 1

    async def test_llm_is_not_consulted_when_rules_are_confident(self) -> None:
        # Spending a network round-trip on an obvious question is waste.
        llm = StubLLM(reply="analyze_governance")
        plan = await Planner(llm=llm).plan("Find datasets without owners")

        assert plan.intent is Intent.FIND_MISSING_OWNERS
        assert llm.calls == 0

    async def test_llm_failure_falls_back_to_the_rule_verdict(self) -> None:
        # Planning must survive a provider outage.
        llm = StubLLM(error=LLMTimeoutError("provider down"))
        plan = await Planner(llm=llm).plan("Anything I should worry about?")

        assert plan.intent is Intent.UNKNOWN
        assert plan.used_llm is False

    async def test_unparseable_llm_reply_is_ignored(self) -> None:
        llm = StubLLM(reply="I'm not sure what you mean")
        plan = await Planner(llm=llm).plan("Anything I should worry about?")
        assert plan.intent is Intent.UNKNOWN


class TestToolSelection:
    async def test_owner_question_skips_lineage_and_statistics(self) -> None:
        # The core agent behaviour: only the needed tools run.
        plan = await Planner().plan("Find datasets without owners")

        assert NODE_OWNERS in plan.nodes
        assert NODE_DATASETS in plan.nodes
        assert NODE_LINEAGE not in plan.nodes
        assert NODE_STATISTICS not in plan.nodes

    async def test_lineage_question_selects_lineage(self) -> None:
        plan = await Planner().plan("What is downstream of fct_payments?")
        assert NODE_LINEAGE in plan.nodes

    async def test_risk_question_gathers_the_widest_evidence(self) -> None:
        plan = await Planner().plan("Which datasets are highest risk?")
        assert {NODE_DATASETS, NODE_OWNERS, NODE_LINEAGE} <= set(plan.nodes)

    async def test_every_plan_ends_in_reasoning(self) -> None:
        # An answer must always be explained, never returned as raw findings.
        for question in [
            "Find datasets without owners",
            "Analyze governance",
            "Generate documentation",
            "Create a report",
        ]:
            plan = await Planner().plan(question)
            assert NODE_REASONING in plan.nodes

    async def test_risk_runs_before_reasoning(self) -> None:
        # Reasoning explains the verdict, so the verdict must already exist.
        plan = await Planner().plan("Which datasets are highest risk?")
        assert plan.nodes.index(NODE_RISK) < plan.nodes.index(NODE_REASONING)

    async def test_report_intent_adds_the_report_node(self) -> None:
        plan = await Planner().plan("Create a governance report")
        assert NODE_REPORT in plan.nodes

    async def test_documentation_intent_skips_recommendations(self) -> None:
        # The document IS the deliverable; a recommendation list is noise.
        plan = await Planner().plan("Generate documentation for stg_orders")
        assert NODE_RECOMMENDATION not in plan.nodes

    async def test_actionable_intents_add_recommendations(self) -> None:
        plan = await Planner().plan("Find datasets without owners")
        assert NODE_RECOMMENDATION in plan.nodes


class TestTargetExtraction:
    async def test_extracts_an_explicit_urn(self) -> None:
        urn = "urn:li:dataset:(urn:li:dataPlatform:hive,fct_payments,PROD)"
        plan = await Planner().plan(f"Why is {urn} risky?")
        assert plan.target_urn == urn

    async def test_extracts_a_snake_case_asset_name(self) -> None:
        plan = await Planner().plan("Why is fct_payments high risk?")
        assert plan.target_name == "fct_payments"

    async def test_extracts_a_dotted_asset_path(self) -> None:
        plan = await Planner().plan("Explain finance.fct_revenue")
        assert plan.target_name == "finance.fct_revenue"

    async def test_ignores_ordinary_domain_words(self) -> None:
        # "datasets" and "owners" must not be mistaken for asset names.
        plan = await Planner().plan("Find datasets without owners")
        assert plan.target_name is None
        assert plan.target_urn is None

    async def test_a_named_target_pulls_lineage_into_the_plan(self) -> None:
        # Blast radius is the first question anyone asks about one asset.
        plan = await Planner().plan("Analyze governance for fct_payments")
        assert NODE_LINEAGE in plan.nodes
