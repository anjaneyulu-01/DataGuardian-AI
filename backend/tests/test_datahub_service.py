"""Service-layer tests.

Cover the decisions this layer owns: what is an error versus a valid empty
result, pagination clamping, and the partial-failure behaviour of statistics.
"""

from collections.abc import Callable

import httpx
import pytest

from app.integrations.datahub import (
    DataHubEntityNotFoundError,
    DataHubService,
    LineageDirection,
    TimeRange,
)
from tests import fixtures
from tests.conftest import Handler, graphql_responder, routing_responder

URN = "urn:li:dataset:(urn:li:dataPlatform:hive,fct_users,PROD)"


class TestDatasets:
    async def test_list_datasets_returns_a_page(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        service = make_service(
            graphql_responder(
                fixtures.search_response(
                    fixtures.DATASET_COMPLETE, fixtures.DATASET_BARE, total=57
                )
            )
        )
        page = await service.get_datasets()
        assert page.total == 57
        assert len(page.results) == 2
        assert page.has_more is True

    async def test_get_dataset_raises_404_for_a_null_entity(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        # DataHub answers HTTP 200 with {"dataset": null} for an unknown URN,
        # so the service must turn that into a 404 itself.
        service = make_service(graphql_responder({"dataset": None}))
        with pytest.raises(DataHubEntityNotFoundError) as excinfo:
            await service.get_dataset(URN)
        assert excinfo.value.status_code == 404
        assert URN in excinfo.value.detail

    async def test_get_dataset_returns_the_model(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        service = make_service(
            graphql_responder({"dataset": fixtures.DATASET_COMPLETE})
        )
        dataset = await service.get_dataset(URN)
        assert dataset.name == "fct_users"
        assert len(dataset.owners) == 2

    async def test_schema_absent_returns_empty_not_error(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        # A dataset without a schema aspect is legitimate.
        service = make_service(
            graphql_responder({"dataset": {"urn": URN, "schemaMetadata": None}})
        )
        schema = await service.get_dataset_schema(URN)
        assert schema.fields == []
        assert schema.field_count == 0


class TestPagination:
    async def test_count_is_clamped_to_the_configured_maximum(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.update(json.loads(request.content)["variables"])
            return httpx.Response(200, json={"data": fixtures.search_response()})

        service = make_service(handler)
        await service.get_datasets(count=10_000)
        # max_page_size is 200 in the test settings.
        assert captured["count"] == 200

    async def test_negative_start_is_floored_to_zero(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.update(json.loads(request.content)["variables"])
            return httpx.Response(200, json={"data": fixtures.search_response()})

        service = make_service(handler)
        await service.get_datasets(start=-5)
        assert captured["start"] == 0

    async def test_none_count_uses_the_configured_default(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.update(json.loads(request.content)["variables"])
            return httpx.Response(200, json={"data": fixtures.search_response()})

        service = make_service(handler)
        await service.get_datasets()
        assert captured["count"] == 20


class TestLineage:
    async def test_direction_is_passed_through(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.update(json.loads(request.content)["variables"])
            return httpx.Response(200, json={"data": fixtures.LINEAGE_DOWNSTREAM})

        service = make_service(handler)
        lineage = await service.get_lineage(URN, LineageDirection.UPSTREAM)
        assert captured["direction"] == "UPSTREAM"
        # The model records what was asked for, not what the fixture happens
        # to contain.
        assert lineage.direction is LineageDirection.UPSTREAM

    async def test_impact_fetches_both_directions(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        service = make_service(graphql_responder(fixtures.LINEAGE_DOWNSTREAM))
        result = await service.get_lineage_both_directions(URN)
        assert set(result) == {"upstream", "downstream"}
        assert result["upstream"].direction is LineageDirection.UPSTREAM
        assert result["downstream"].direction is LineageDirection.DOWNSTREAM


class TestOwners:
    async def test_dataset_owners_path(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        service = make_service(
            graphql_responder({"dataset": fixtures.DATASET_COMPLETE})
        )
        owners = await service.get_owners(dataset_urn=URN)
        assert {o.urn for o in owners} == {
            "urn:li:corpuser:aditi",
            "urn:li:corpGroup:platform",
        }

    async def test_catalogue_wide_owners_use_aggregation(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        service = make_service(graphql_responder(fixtures.OWNER_AGGREGATIONS))
        owners = await service.get_owners()
        assert {o.asset_count for o in owners} == {12, 3}

    async def test_owners_of_a_missing_dataset_raise_404(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        service = make_service(graphql_responder({"dataset": None}))
        with pytest.raises(DataHubEntityNotFoundError):
            await service.get_owners(dataset_urn=URN)


class TestStatistics:
    async def test_profiles_and_usage_are_combined(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        service = make_service(
            routing_responder(
                {
                    "getDatasetProfiles": httpx.Response(
                        200, json={"data": fixtures.PROFILES_RESPONSE}
                    ),
                    "getDatasetUsage": httpx.Response(
                        200, json={"data": fixtures.USAGE_RESPONSE}
                    ),
                }
            )
        )
        stats = await service.get_statistics(URN, TimeRange.MONTH)
        assert stats.latest_profile is not None
        assert stats.latest_profile.row_count == 1000
        assert stats.usage is not None
        assert stats.usage.total_queries == 128
        assert stats.usage_unavailable_reason is None

    async def test_usage_failure_does_not_lose_the_profiles(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        # Most quickstart instances have no usage source. Losing profiling
        # data because of that would be the wrong trade.
        service = make_service(
            routing_responder(
                {
                    "getDatasetProfiles": httpx.Response(
                        200, json={"data": fixtures.PROFILES_RESPONSE}
                    ),
                    "getDatasetUsage": httpx.Response(
                        200,
                        json={
                            "errors": [{"message": "Cannot query field 'usageStats'"}]
                        },
                    ),
                }
            )
        )
        stats = await service.get_statistics(URN)
        assert stats.latest_profile is not None
        assert stats.usage is None
        # The caller must be able to distinguish "no usage" from "usage broke".
        assert stats.usage_unavailable_reason is not None
        assert "usageStats" in stats.usage_unavailable_reason

    async def test_profile_failure_is_not_swallowed(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        service = make_service(graphql_responder({"dataset": None}))
        with pytest.raises(DataHubEntityNotFoundError):
            await service.get_statistics(URN)


class TestHealth:
    async def test_unreachable_datahub_is_reported_not_raised(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        service = make_service(handler)
        health = await service.check_health()

        assert health.reachable is False
        assert health.error is not None
        assert "datahub.test" in health.error
        # Configuration is still reported, which is what makes the response
        # actionable.
        assert health.authenticated is True
        assert health.gms_url == "http://datahub.test:8080"

    async def test_reachable_datahub_reports_version(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        service = make_service(
            lambda _r: httpx.Response(
                200,
                json={"versions": {"acryldata/datahub": {"version": "v0.13.3"}}},
            )
        )
        health = await service.check_health()
        assert health.reachable is True
        assert health.version == "v0.13.3"
        assert health.latency_ms is not None

    async def test_non_datahub_server_on_the_port_is_detected(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        # Exactly the situation on this machine: an unrelated dev server
        # answering on 8080.
        service = make_service(
            lambda _r: httpx.Response(404, text="Cannot GET /config")
        )
        health = await service.check_health()
        assert health.reachable is False
        assert health.error is not None
        assert "404" in health.error
