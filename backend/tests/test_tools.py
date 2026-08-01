"""Tests for the agent-facing tools.

The tools are thin, so these tests focus on the parts that are not: argument
coercion (a language model will send lowercase enum values), the compact
summary shape, and the guarantee that typed DataHub errors still propagate.
"""

from collections.abc import Callable

import pytest

from app.integrations.datahub import (
    DataHubEntityNotFoundError,
    DataHubService,
    LineageDirection,
)
from app.tools import build_tools
from tests import fixtures
from tests.conftest import Handler, graphql_responder, routing_responder

URN = "urn:li:dataset:(urn:li:dataPlatform:hive,fct_users,PROD)"


class TestToolkit:
    def test_every_tool_advertises_a_name_and_description(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        tools = build_tools(make_service(graphql_responder({})))
        described = tools.describe()

        assert len(described) == 5
        names = {d["name"] for d in described}
        assert names == {
            "datahub_datasets",
            "datahub_lineage",
            "datahub_owners",
            "datahub_domains",
            "datahub_statistics",
        }
        # A blank description is useless in an LLM tool manifest.
        assert all(len(d["description"]) > 40 for d in described)

    def test_serialize_produces_json_safe_output(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        from app.integrations.datahub import Owner, OwnerKind
        from app.tools.base import DataHubTool

        owner = Owner(urn="urn:li:corpuser:x", kind=OwnerKind.USER)
        payload = DataHubTool.serialize([owner])

        assert isinstance(payload, list)
        # Enums render as their value, not "OwnerKind.USER".
        assert payload[0]["kind"] == "USER"


class TestDatasetTool:
    async def test_list_and_get(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        tools = build_tools(
            make_service(
                graphql_responder(
                    fixtures.search_response(fixtures.DATASET_COMPLETE, total=1)
                )
            )
        )
        page = await tools.datasets.list(count=5)
        assert page.total == 1
        assert page.results[0].name == "fct_users"

    async def test_filters_report_without_judging(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        tools = build_tools(
            make_service(
                graphql_responder(
                    fixtures.search_response(
                        fixtures.DATASET_COMPLETE, fixtures.DATASET_BARE, total=2
                    )
                )
            )
        )
        undocumented = await tools.datasets.list_undocumented()
        unowned = await tools.datasets.list_unowned()

        # Only the bare dataset lacks both.
        assert [d.urn for d in undocumented] == [fixtures.DATASET_BARE["urn"]]
        assert [d.urn for d in unowned] == [fixtures.DATASET_BARE["urn"]]

    async def test_not_found_propagates_to_the_agent(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        # Tools must not swallow typed errors: the agent needs to tell
        # "does not exist" from "try again later".
        tools = build_tools(make_service(graphql_responder({"dataset": None})))
        with pytest.raises(DataHubEntityNotFoundError):
            await tools.datasets.get(URN)


class TestLineageTool:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("UPSTREAM", LineageDirection.UPSTREAM),
            ("upstream", LineageDirection.UPSTREAM),
            ("  Downstream  ", LineageDirection.DOWNSTREAM),
        ],
    )
    async def test_direction_accepts_llm_casing(
        self,
        make_service: Callable[[Handler], DataHubService],
        raw: str,
        expected: LineageDirection,
    ) -> None:
        tools = build_tools(
            make_service(graphql_responder(fixtures.LINEAGE_DOWNSTREAM))
        )
        lineage = await tools.lineage.get(URN, direction=raw)
        assert lineage.direction is expected

    async def test_invalid_direction_fails_loudly(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        # Silently defaulting would give the agent a confidently wrong answer.
        tools = build_tools(
            make_service(graphql_responder(fixtures.LINEAGE_DOWNSTREAM))
        )
        with pytest.raises(ValueError, match="Invalid lineage direction"):
            await tools.lineage.get(URN, direction="sideways")

    async def test_downstream_count(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        tools = build_tools(
            make_service(graphql_responder(fixtures.LINEAGE_DOWNSTREAM))
        )
        assert await tools.lineage.downstream_count(URN) == 2


class TestOwnerAndDomainTools:
    async def test_has_owner_is_false_for_an_unowned_dataset(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        tools = build_tools(
            make_service(graphql_responder({"dataset": fixtures.DATASET_BARE}))
        )
        assert await tools.owners.has_owner(URN) is False

    async def test_has_owner_is_true_when_owned(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        tools = build_tools(
            make_service(graphql_responder({"dataset": fixtures.DATASET_COMPLETE}))
        )
        assert await tools.owners.has_owner(URN) is True

    async def test_domain_names_are_compact(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        tools = build_tools(make_service(graphql_responder(fixtures.DOMAINS_RESPONSE)))
        assert await tools.domains.names() == ["Analytics"]


class TestStatisticsTool:
    async def test_summary_is_flat_and_prompt_sized(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        tools = build_tools(
            make_service(
                routing_responder(
                    {
                        "getDatasetProfiles": __import__("httpx").Response(
                            200, json={"data": fixtures.PROFILES_RESPONSE}
                        ),
                        "getDatasetUsage": __import__("httpx").Response(
                            200, json={"data": fixtures.USAGE_RESPONSE}
                        ),
                    }
                )
            )
        )
        summary = await tools.statistics.summary(URN)

        assert summary["profiled"] is True
        assert summary["row_count"] == 1000
        assert summary["usage_available"] is True
        assert summary["total_queries"] == 128
        # Flat and small — no nested field profiles.
        assert all(not isinstance(v, dict | list) for v in summary.values())

    async def test_summary_distinguishes_absent_from_zero(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        # The agent must not read "no statistics available" as a healthy zero.
        tools = build_tools(
            make_service(
                graphql_responder({"dataset": {"urn": URN, "datasetProfiles": []}})
            )
        )
        summary = await tools.statistics.summary(URN)

        assert summary["profiled"] is False
        assert summary["row_count"] is None
        assert summary["usage_available"] is False

    async def test_invalid_time_range_fails_loudly(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        tools = build_tools(make_service(graphql_responder({})))
        with pytest.raises(ValueError, match="Invalid time range"):
            await tools.statistics.summary(URN, time_range="fortnight")
