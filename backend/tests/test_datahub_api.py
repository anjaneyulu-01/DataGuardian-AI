"""End-to-end API tests.

Drive the real FastAPI app over HTTP with only the DataHub network boundary
mocked, so routing, dependency injection, response serialisation, and the
exception handlers are all exercised.
"""

from collections.abc import Callable
from typing import Any

import httpx

from tests import fixtures
from tests.conftest import (
    Handler,
    graphql_responder,
    raising_responder,
    routing_responder,
)

URN = "urn:li:dataset:(urn:li:dataPlatform:hive,fct_users,PROD)"


class TestDatasetEndpoints:
    def test_list_datasets(self, api_client: Callable[[Handler], Any]) -> None:
        with api_client(
            graphql_responder(
                fixtures.search_response(fixtures.DATASET_COMPLETE, total=1)
            )
        ) as client:
            response = client.get("/api/v1/datasets")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["has_more"] is False
        assert body["results"][0]["name"] == "fct_users"
        # snake_case throughout, regardless of GraphQL's camelCase.
        assert body["results"][0]["qualified_name"] == "prod.analytics.fct_users"

    def test_get_dataset_by_urn_in_path(
        self, api_client: Callable[[Handler], Any]
    ) -> None:
        with api_client(
            graphql_responder({"dataset": fixtures.DATASET_COMPLETE})
        ) as client:
            # A raw URN with colons, commas, and parentheses must route.
            response = client.get(f"/api/v1/datasets/{URN}")

        assert response.status_code == 200
        assert response.json()["urn"] == URN

    def test_unknown_dataset_returns_404(
        self, api_client: Callable[[Handler], Any]
    ) -> None:
        with api_client(graphql_responder({"dataset": None})) as client:
            response = client.get(f"/api/v1/datasets/{URN}")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_page_size_over_the_limit_is_rejected_by_validation(
        self, api_client: Callable[[Handler], Any]
    ) -> None:
        with api_client(graphql_responder(fixtures.search_response())) as client:
            response = client.get("/api/v1/datasets", params={"count": 5000})

        assert response.status_code == 422


class TestFailureTranslation:
    def test_unreachable_datahub_becomes_503(
        self, api_client: Callable[[Handler], Any]
    ) -> None:
        with api_client(
            raising_responder(httpx.ConnectError("connection refused"))
        ) as client:
            response = client.get("/api/v1/datasets")

        assert response.status_code == 503
        assert "datahub.test" in response.json()["detail"]

    def test_timeout_becomes_504(self, api_client: Callable[[Handler], Any]) -> None:
        with api_client(raising_responder(httpx.ReadTimeout("slow"))) as client:
            response = client.get("/api/v1/datasets")

        assert response.status_code == 504

    def test_graphql_schema_mismatch_becomes_502(
        self, api_client: Callable[[Handler], Any]
    ) -> None:
        with api_client(
            graphql_responder(errors=[{"message": "Cannot query field 'x'"}])
        ) as client:
            response = client.get("/api/v1/datasets")

        assert response.status_code == 502
        assert "Cannot query field" in response.json()["detail"]

    def test_rejected_token_becomes_502_not_401(
        self, api_client: Callable[[Handler], Any]
    ) -> None:
        # 401 would wrongly suggest the caller of *our* API is unauthenticated.
        with api_client(lambda _r: httpx.Response(403)) as client:
            response = client.get("/api/v1/datasets")

        assert response.status_code == 502
        assert "DATAHUB_TOKEN" in response.json()["detail"]


class TestHealthEndpoints:
    def test_liveness_does_not_touch_datahub(
        self, api_client: Callable[[Handler], Any]
    ) -> None:
        def exploding(_request: httpx.Request) -> httpx.Response:
            raise AssertionError("liveness must not call DataHub")

        with api_client(exploding) as client:
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_datahub_health_reports_outage_as_200(
        self, api_client: Callable[[Handler], Any]
    ) -> None:
        with api_client(
            raising_responder(httpx.ConnectError("connection refused"))
        ) as client:
            response = client.get("/api/v1/health/datahub")

        # 200 with reachable=false: a monitoring endpoint should explain
        # itself rather than fail.
        assert response.status_code == 200
        body = response.json()
        assert body["reachable"] is False
        assert body["gms_url"] == "http://datahub.test:8080"
        assert body["authenticated"] is True
        assert "connection refused" in body["error"]


class TestOtherEndpoints:
    def test_owners_endpoint(self, api_client: Callable[[Handler], Any]) -> None:
        with api_client(graphql_responder(fixtures.OWNER_AGGREGATIONS)) as client:
            response = client.get("/api/v1/owners")

        assert response.status_code == 200
        assert {o["asset_count"] for o in response.json()} == {12, 3}

    def test_domains_endpoint(self, api_client: Callable[[Handler], Any]) -> None:
        with api_client(graphql_responder(fixtures.DOMAINS_RESPONSE)) as client:
            response = client.get("/api/v1/domains")

        assert response.status_code == 200
        assert response.json()["results"][0]["entity_count"] == 42

    def test_lineage_endpoint_requires_a_urn(
        self, api_client: Callable[[Handler], Any]
    ) -> None:
        with api_client(graphql_responder(fixtures.LINEAGE_DOWNSTREAM)) as client:
            missing = client.get("/api/v1/lineage")
            ok = client.get(
                "/api/v1/lineage", params={"urn": URN, "direction": "UPSTREAM"}
            )

        assert missing.status_code == 422
        assert ok.status_code == 200
        assert ok.json()["direction"] == "UPSTREAM"

    def test_impact_endpoint_returns_both_directions(
        self, api_client: Callable[[Handler], Any]
    ) -> None:
        with api_client(graphql_responder(fixtures.LINEAGE_DOWNSTREAM)) as client:
            response = client.get("/api/v1/lineage/impact", params={"urn": URN})

        assert response.status_code == 200
        assert set(response.json()) == {"upstream", "downstream"}

    def test_statistics_endpoint(self, api_client: Callable[[Handler], Any]) -> None:
        with api_client(
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
        ) as client:
            response = client.get("/api/v1/statistics", params={"urn": URN})

        assert response.status_code == 200
        body = response.json()
        assert body["latest_profile"]["row_count"] == 1000
        assert body["usage"]["total_queries"] == 128


class TestOpenAPI:
    def test_every_datahub_endpoint_is_documented(
        self, api_client: Callable[[Handler], Any]
    ) -> None:
        with api_client(graphql_responder({})) as client:
            schema = client.get("/openapi.json").json()

        paths = set(schema["paths"])
        assert {
            "/api/v1/health",
            "/api/v1/health/datahub",
            "/api/v1/datasets",
            "/api/v1/datasets/{urn}",
            "/api/v1/owners",
            "/api/v1/domains",
            "/api/v1/domains/{urn}",
            "/api/v1/lineage",
            "/api/v1/lineage/impact",
            "/api/v1/statistics",
        } <= paths
