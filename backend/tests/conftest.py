"""Shared test fixtures.

Tests drive the real client, GraphQL, mapper, and service code and replace
only the network boundary with `httpx.MockTransport`. Nothing below the
transport is stubbed, so a broken query document or a mapper regression fails
the suite.

The GraphQL payloads in `tests/fixtures.py` are *test doubles*, not sample
data: they exist to exercise the mapper's handling of sparse and malformed
metadata, and the application never serves them.
"""

import json
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_app_settings, get_datahub_client
from app.config import Settings
from app.integrations.datahub import DataHubClient, DataHubService, GraphQLClient

# A transport handler: takes a request, returns a canned response.
Handler = Callable[[httpx.Request], httpx.Response]

# Environment variables that would otherwise leak a developer's real
# configuration into the suite. Cleared for every test.
_LEAKY_ENV_PREFIXES = ("LLM_", "XAI_", "GROQ_", "GEMINI_", "DATAHUB_", "OPENAI_")


@pytest.fixture(autouse=True)
def hermetic_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate `Settings` from the developer's real environment.

    The project keeps ONE .env at the repository root, and `Settings` resolves
    it by absolute path — so without this fixture every `Settings()` built in a
    test would silently inherit whatever the developer happens to have
    configured locally. A test asserting the default provider would then pass
    or fail depending on someone's personal API keys.

    Both sources are neutralised: the .env file, and any matching variables
    already exported in the shell.
    """
    monkeypatch.setitem(Settings.model_config, "env_file", None)  # type: ignore[typeddict-item]
    for name in list(os.environ):
        if name.upper().startswith(_LEAKY_ENV_PREFIXES):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def datahub_settings() -> Settings:
    """Settings pointing at a deliberately unroutable DataHub host.

    Retries are disabled so failure-path tests do not spend real time backing
    off, and the timeout is short for the same reason.
    """
    return Settings(
        datahub_gms_url="http://datahub.test:8080",
        datahub_token="test-token",
        datahub_timeout_seconds=5.0,
        datahub_max_retries=0,
        datahub_default_page_size=20,
        datahub_max_page_size=200,
    )


@pytest.fixture
def make_client(datahub_settings: Settings) -> Callable[[Handler], DataHubClient]:
    """Build a `DataHubClient` whose transport is a caller-supplied handler."""

    def factory(handler: Handler) -> DataHubClient:
        return DataHubClient(
            settings=datahub_settings, transport=httpx.MockTransport(handler)
        )

    return factory


@pytest.fixture
def make_service(
    make_client: Callable[[Handler], DataHubClient], datahub_settings: Settings
) -> Callable[[Handler], DataHubService]:
    """Build a `DataHubService` wired to a mock transport."""

    def factory(handler: Handler) -> DataHubService:
        client = make_client(handler)
        return DataHubService(
            graphql=GraphQLClient(client), client=client, settings=datahub_settings
        )

    return factory


@pytest.fixture
def api_client(
    make_client: Callable[[Handler], DataHubClient], datahub_settings: Settings
) -> Callable[[Handler], Any]:
    """Drive the real FastAPI app with a mocked DataHub transport.

    Exercises the whole HTTP path — routing, dependency injection, response
    serialisation, and the exception handlers — by overriding only the
    dependency that yields the DataHub client.
    """

    @contextmanager
    def factory(handler: Handler) -> Iterator[TestClient]:
        from app.main import app

        client = make_client(handler)
        app.dependency_overrides[get_datahub_client] = lambda: client
        app.dependency_overrides[get_app_settings] = lambda: datahub_settings
        try:
            with TestClient(app) as test_client:
                yield test_client
        finally:
            app.dependency_overrides.clear()

    return factory


# ---------------------------------------------------------------------------
# Transport handlers
# ---------------------------------------------------------------------------


def graphql_responder(
    data: dict[str, Any] | None = None,
    errors: list[dict[str, Any]] | None = None,
    status_code: int = 200,
) -> Handler:
    """Return one GraphQL envelope for any request."""

    def handler(_request: httpx.Request) -> httpx.Response:
        body: dict[str, Any] = {}
        if data is not None:
            body["data"] = data
        if errors is not None:
            body["errors"] = errors
        return httpx.Response(status_code, json=body)

    return handler


def routing_responder(by_operation: dict[str, httpx.Response]) -> Handler:
    """Dispatch on the GraphQL `operationName` in the request body.

    Needed by tests covering calls that issue more than one query, such as
    statistics (profiles plus usage) and impact analysis.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content or b"{}")
        operation = payload.get("operationName", "")
        if operation not in by_operation:
            return httpx.Response(
                200,
                json={"errors": [{"message": f"unexpected operation: {operation}"}]},
            )
        return by_operation[operation]

    return handler


def raising_responder(exc: Exception) -> Handler:
    """Raise a transport-level exception, simulating a network failure."""

    def handler(_request: httpx.Request) -> httpx.Response:
        raise exc

    return handler
