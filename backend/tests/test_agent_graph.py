"""Graph execution tests.

These run the REAL compiled LangGraph, the real planner, the real risk engine,
and the real nodes — only the LLM and the Tool layer are doubles. So a broken
edge, a bad router, or a node that forgets to write its state key fails here.
"""

import pytest

from app.agents import GovernanceAgent, Intent, Planner, RiskLevel
from app.agents.state import NodeStatus
from app.integrations.datahub import DataHubEntityNotFoundError
from app.llm.exceptions import LLMTimeoutError
from tests.agent_doubles import (
    StubLLM,
    called_tools,
    make_dataset,
    make_toolkit,
)


def build_agent(
    toolkit=None,
    llm=None,
    **toolkit_kwargs,
) -> GovernanceAgent:
    """Agent wired to doubles, with the real graph and real planner."""
    resolved_toolkit = toolkit or make_toolkit(**toolkit_kwargs)
    resolved_llm = llm or StubLLM()
    return GovernanceAgent(
        toolkit=resolved_toolkit,
        llm=resolved_llm,
        # Deterministic planning: these tests assert routing, not classification.
        planner=Planner(llm=None),
    )


class TestEndToEnd:
    async def test_returns_the_documented_json_shape(self) -> None:
        agent = build_agent(datasets=[make_dataset(owned=False, documented=False)])
        result = await agent.analyze("Find datasets without owners")

        payload = result.model_dump()
        for key in (
            "summary",
            "risk_level",
            "risk_score",
            "findings",
            "recommendations",
            "evidence",
        ):
            assert key in payload

    async def test_unowned_dataset_produces_a_finding_and_a_score(self) -> None:
        agent = build_agent(datasets=[make_dataset(owned=False)])
        result = await agent.analyze("Find datasets without owners")

        assert result.intent is Intent.FIND_MISSING_OWNERS
        assert result.risk_score > 0
        assert "missing_owner" in {f.rule for f in result.findings}
        assert not result.degraded

    async def test_clean_catalogue_scores_zero(self) -> None:
        agent = build_agent(datasets=[make_dataset(owned=True, documented=True)])
        result = await agent.analyze("Find datasets without owners")

        assert result.risk_score == 0
        assert result.risk_level is RiskLevel.LOW
        assert result.findings == []


class TestConditionalRouting:
    async def test_owner_question_never_calls_lineage_or_statistics(self) -> None:
        # The defining agent behaviour: tools are selected, not all invoked.
        toolkit = make_toolkit(datasets=[make_dataset(owned=False)])
        agent = build_agent(toolkit=toolkit)

        await agent.analyze("Find datasets without owners")

        used = called_tools(toolkit)
        assert "datasets" in used
        assert "owners" in used
        assert "lineage" not in used
        assert "statistics" not in used

    async def test_lineage_question_calls_lineage(self) -> None:
        toolkit = make_toolkit(datasets=[make_dataset()], downstream_total=7)
        agent = build_agent(toolkit=toolkit)

        await agent.analyze("What is downstream of this data?")

        assert "lineage" in called_tools(toolkit)

    async def test_governance_question_calls_statistics(self) -> None:
        toolkit = make_toolkit(datasets=[make_dataset()])
        agent = build_agent(toolkit=toolkit)

        await agent.analyze("Analyze governance health")

        assert "statistics" in called_tools(toolkit)

    async def test_report_intent_runs_the_report_node(self) -> None:
        agent = build_agent(datasets=[make_dataset(owned=False)])
        result = await agent.analyze("Create a governance report")

        assert result.intent is Intent.GENERATE_REPORT
        assert "report" in result.tools_used

    async def test_trace_records_only_nodes_that_ran(self) -> None:
        agent = build_agent(datasets=[make_dataset(owned=False)])
        result = await agent.analyze("Find datasets without owners")

        executed = {t.node for t in result.trace}
        assert "planner" in executed
        assert "lineage" not in executed
        # Every recorded node has a measured duration.
        assert all(t.duration_ms >= 0 for t in result.trace)


class TestLineageFeedsRisk:
    async def test_downstream_count_from_lineage_raises_the_score(self) -> None:
        # Proves evidence flows between nodes rather than each running in
        # isolation: the lineage node's output changes the risk node's verdict.
        low = make_toolkit(datasets=[make_dataset()], downstream_total=0)
        high = make_toolkit(datasets=[make_dataset()], downstream_total=15)

        low_result = await build_agent(toolkit=low).analyze("Show downstream impact")
        high_result = await build_agent(toolkit=high).analyze("Show downstream impact")

        assert high_result.risk_score > low_result.risk_score
        assert "large_downstream_impact" in {f.rule for f in high_result.findings}


class TestErrorHandling:
    async def test_tool_failure_degrades_instead_of_crashing(self) -> None:
        agent = build_agent(dataset_error=DataHubEntityNotFoundError("gone"))
        result = await agent.analyze("Find datasets without owners")

        assert result.degraded is True
        assert result.errors
        # Still a usable answer, not an exception.
        assert result.summary

    async def test_failed_node_is_marked_in_the_trace(self) -> None:
        agent = build_agent(dataset_error=DataHubEntityNotFoundError("gone"))
        result = await agent.analyze("Find datasets without owners")

        failed = [t for t in result.trace if t.status is NodeStatus.FAILED]
        assert failed
        assert failed[0].error

    async def test_graph_continues_after_a_tool_failure(self) -> None:
        # Containment means later nodes still run on partial evidence.
        agent = build_agent(
            datasets=[make_dataset()], lineage_error=LLMTimeoutError("slow")
        )
        result = await agent.analyze("Show downstream impact of the data")

        assert "reasoning" in result.tools_used
        assert result.degraded is True

    async def test_llm_outage_still_produces_a_factual_answer(self) -> None:
        # The deterministic fallback: no prose model, but the findings and the
        # score are unaffected because neither came from the LLM.
        agent = build_agent(
            datasets=[make_dataset(owned=False, documented=False)],
            llm=StubLLM(error=LLMTimeoutError("all providers down")),
        )
        result = await agent.analyze("Find datasets without owners")

        assert result.degraded is True
        assert result.risk_score > 0
        assert result.findings
        assert (
            "missing_owner" in result.summary.lower()
            or "violation" in result.summary.lower()
        )
        # Fallback recommendations are still actionable.
        assert result.recommendations

    async def test_empty_catalogue_is_answered_honestly(self) -> None:
        agent = build_agent(datasets=[])
        result = await agent.analyze("Find datasets without owners")

        assert result.risk_score == 0
        assert result.findings == []
        assert not result.degraded


class TestObservability:
    async def test_trace_covers_every_executed_node_in_order(self) -> None:
        agent = build_agent(datasets=[make_dataset(owned=False)])
        result = await agent.analyze("Which datasets are highest risk?")

        nodes = [t.node for t in result.trace]
        assert nodes[0] == "planner"
        assert nodes.index("risk") < nodes.index("reasoning")

    async def test_result_reports_duration_and_provider(self) -> None:
        agent = build_agent(datasets=[make_dataset()])
        result = await agent.analyze("Analyze governance")

        assert result.duration_ms > 0
        assert result.llm_provider == "stub"

    async def test_tools_used_lists_successful_nodes_only(self) -> None:
        agent = build_agent(dataset_error=DataHubEntityNotFoundError("gone"))
        result = await agent.analyze("Find datasets without owners")

        assert "datasets" not in result.tools_used
        assert "planner" in result.tools_used


class TestEvidenceBoundary:
    async def test_llm_receives_evidence_not_a_datahub_client(self) -> None:
        # The architectural guarantee: the model only ever sees serialised
        # facts the Tool layer produced.
        llm = StubLLM()
        agent = build_agent(datasets=[make_dataset(owned=False)], llm=llm)
        await agent.analyze("Find datasets without owners")

        assert llm.prompts
        prompt = llm.prompts[0]
        assert "fct_orders" in prompt
        assert "missing_owner" in prompt

    async def test_risk_score_is_absent_from_llm_control(self) -> None:
        # Two runs with different stub replies must produce the same score,
        # because the score never depends on model output.
        first = await build_agent(
            datasets=[make_dataset(owned=False)], llm=StubLLM(reply="A")
        ).analyze("Find datasets without owners")
        second = await build_agent(
            datasets=[make_dataset(owned=False)], llm=StubLLM(reply="B")
        ).analyze("Find datasets without owners")

        assert first.risk_score == second.risk_score
        assert {f.rule for f in first.findings} == {f.rule for f in second.findings}


@pytest.mark.parametrize(
    "question,expected_intent",
    [
        ("Find datasets without owners", Intent.FIND_MISSING_OWNERS),
        ("Which datasets are highest risk?", Intent.FIND_RISKY_DATASETS),
        ("Show downstream impact", Intent.ANALYZE_LINEAGE),
        ("Analyze governance health", Intent.ANALYZE_GOVERNANCE),
        ("Create a governance report", Intent.GENERATE_REPORT),
    ],
)
async def test_each_intent_runs_end_to_end(
    question: str, expected_intent: Intent
) -> None:
    """Smoke test: every supported intent completes without error."""
    agent = build_agent(datasets=[make_dataset(owned=False)])
    result = await agent.analyze(question)

    assert result.intent is expected_intent
    assert result.summary
    assert result.duration_ms > 0
