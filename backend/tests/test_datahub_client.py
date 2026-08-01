"""Transport and GraphQL envelope tests.

These cover the failure paths, which is where an integration layer earns its
keep. Every one of these conditions happens in practice against a real
DataHub.
"""

from collections.abc import Callable

import httpx
import pytest

from app.config import Settings
from app.integrations.datahub import (
    DataHubAuthenticationError,
    DataHubClient,
    DataHubConnectionError,
    DataHubQueryError,
    DataHubResponseError,
    DataHubTimeoutError,
    GraphQLClient,
)
from tests.conftest import Handler, graphql_responder, raising_responder


def _graphql(client: DataHubClient) -> GraphQLClient:
    return GraphQLClient(client)


class TestAuthentication:
    def test_token_becomes_a_bearer_header(self) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return httpx.Response(200, json={"data": {}})

        settings = Settings(datahub_token="secret-token")
        client = DataHubClient(
            settings=settings, transport=httpx.MockTransport(handler)
        )
        assert client.is_authenticated

        import anyio

        anyio.run(lambda: client.post_graphql({"query": "{ __typename }"}))
        assert captured["authorization"] == "Bearer secret-token"

    def test_no_token_sends_no_authorization_header(self) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return httpx.Response(200, json={"data": {}})

        settings = Settings(datahub_token=None)
        client = DataHubClient(
            settings=settings, transport=httpx.MockTransport(handler)
        )
        assert not client.is_authenticated

        import anyio

        anyio.run(lambda: client.post_graphql({"query": "{ __typename }"}))
        assert "authorization" not in captured

    @pytest.mark.parametrize("status_code", [401, 403])
    async def test_rejected_credentials_raise_auth_error(
        self, make_client: Callable[[Handler], DataHubClient], status_code: int
    ) -> None:
        client = make_client(lambda _r: httpx.Response(status_code))
        with pytest.raises(DataHubAuthenticationError) as excinfo:
            await _graphql(client).execute("{ __typename }")
        # The message must say what to fix, not just that it failed.
        assert "DATAHUB_TOKEN" in excinfo.value.detail


class TestTransportFailures:
    async def test_connection_refused_maps_to_connection_error(
        self, make_client: Callable[[Handler], DataHubClient]
    ) -> None:
        client = make_client(
            raising_responder(httpx.ConnectError("connection refused"))
        )
        with pytest.raises(DataHubConnectionError) as excinfo:
            await _graphql(client).execute("{ __typename }")
        # The URL we tried belongs in the message; it is the first thing an
        # operator checks.
        assert "datahub.test" in excinfo.value.detail
        assert excinfo.value.status_code == 503

    async def test_timeout_maps_to_timeout_error(
        self, make_client: Callable[[Handler], DataHubClient]
    ) -> None:
        client = make_client(raising_responder(httpx.ReadTimeout("too slow")))
        with pytest.raises(DataHubTimeoutError) as excinfo:
            await _graphql(client).execute("{ __typename }")
        assert excinfo.value.status_code == 504


class TestGraphQLEnvelope:
    async def test_graphql_errors_raise_even_on_http_200(
        self, make_client: Callable[[Handler], DataHubClient]
    ) -> None:
        # The central reason `graphql.py` exists: GraphQL reports failure with
        # HTTP 200, so a naive caller would read `data` as None and fail later
        # with a confusing mapping error.
        client = make_client(
            graphql_responder(
                errors=[{"message": "Cannot query field 'nope' on type 'Dataset'"}]
            )
        )
        with pytest.raises(DataHubQueryError) as excinfo:
            await _graphql(client).execute("{ nope }", operation_name="probe")
        assert "Cannot query field" in excinfo.value.detail
        assert len(excinfo.value.errors) == 1

    async def test_html_response_raises_a_readable_error(
        self, make_client: Callable[[Handler], DataHubClient]
    ) -> None:
        # A proxy or login page returning HTML is a common misconfiguration.
        client = make_client(
            lambda _r: httpx.Response(200, text="<html><body>Login</body></html>")
        )
        with pytest.raises(DataHubResponseError) as excinfo:
            await _graphql(client).execute("{ __typename }")
        assert "non-JSON" in excinfo.value.detail

    async def test_missing_data_key_raises(
        self, make_client: Callable[[Handler], DataHubClient]
    ) -> None:
        client = make_client(lambda _r: httpx.Response(200, json={}))
        with pytest.raises(DataHubResponseError):
            await _graphql(client).execute("{ __typename }")

    async def test_server_error_includes_a_body_preview(
        self, make_client: Callable[[Handler], DataHubClient]
    ) -> None:
        client = make_client(lambda _r: httpx.Response(500, text="upstream exploded"))
        with pytest.raises(DataHubResponseError) as excinfo:
            await _graphql(client).execute("{ __typename }")
        assert "500" in excinfo.value.detail
        assert "upstream exploded" in excinfo.value.detail

    async def test_variables_are_sent_not_interpolated(
        self, make_client: Callable[[Handler], DataHubClient]
    ) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.update(json.loads(request.content))
            return httpx.Response(200, json={"data": {"ok": True}})

        client = make_client(handler)
        urn = 'urn:li:dataset:(urn:li:dataPlatform:hive,"weird,name",PROD)'
        await _graphql(client).execute(
            "query q($urn: String!) { dataset(urn: $urn) { urn } }",
            {"urn": urn},
            operation_name="q",
        )
        # The URN travels as a variable, so its quotes and commas need no
        # escaping and cannot alter the query.
        assert captured["variables"] == {"urn": urn}
        assert captured["operationName"] == "q"
