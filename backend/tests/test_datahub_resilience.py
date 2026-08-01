"""Tests for the retry policy and the TTL cache.

Both are correctness-critical in ways that are easy to get subtly wrong:
retrying something deterministic wastes time, and caching a failure turns a
blip into a minute-long outage.
"""

import asyncio
from collections.abc import Callable

import httpx
import pytest

from app.integrations.datahub import (
    DataHubAuthenticationError,
    DataHubConnectionError,
    DataHubQueryError,
    DataHubService,
    DataHubTimeoutError,
)
from app.integrations.datahub.cache import NullCache, TTLCache, build_cache_key
from app.integrations.datahub.retry import is_retryable, with_retry
from tests import fixtures
from tests.conftest import Handler


class TestRetryClassification:
    def test_transient_failures_are_retryable(self) -> None:
        assert is_retryable(DataHubConnectionError("refused"))
        assert is_retryable(DataHubTimeoutError("slow"))

    def test_deterministic_failures_are_not_retryable(self) -> None:
        # Retrying these can only ever waste time and multiply log noise.
        assert not is_retryable(DataHubAuthenticationError("bad token"))
        assert not is_retryable(DataHubQueryError("schema mismatch"))


class TestWithRetry:
    async def test_succeeds_without_retrying(self) -> None:
        calls = 0

        async def operation() -> str:
            nonlocal calls
            calls += 1
            return "ok"

        result = await with_retry(operation, attempts=3, base_delay=0.0, max_delay=0.0)
        assert result == "ok"
        assert calls == 1

    async def test_retries_transient_failure_then_succeeds(self) -> None:
        calls = 0

        async def operation() -> str:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise DataHubConnectionError("refused")
            return "ok"

        result = await with_retry(operation, attempts=3, base_delay=0.0, max_delay=0.0)
        assert result == "ok"
        assert calls == 3

    async def test_gives_up_after_the_attempt_budget(self) -> None:
        calls = 0

        async def operation() -> str:
            nonlocal calls
            calls += 1
            raise DataHubTimeoutError("slow")

        with pytest.raises(DataHubTimeoutError):
            await with_retry(operation, attempts=3, base_delay=0.0, max_delay=0.0)
        assert calls == 3

    async def test_does_not_retry_a_deterministic_failure(self) -> None:
        calls = 0

        async def operation() -> str:
            nonlocal calls
            calls += 1
            raise DataHubAuthenticationError("bad token")

        with pytest.raises(DataHubAuthenticationError):
            await with_retry(operation, attempts=5, base_delay=0.0, max_delay=0.0)
        # One attempt only: a rejected token will be rejected again.
        assert calls == 1

    async def test_original_exception_type_is_preserved(self) -> None:
        async def operation() -> str:
            raise DataHubTimeoutError("slow")

        # Callers switch on the type, so it must not be wrapped.
        with pytest.raises(DataHubTimeoutError):
            await with_retry(operation, attempts=2, base_delay=0.0, max_delay=0.0)


class TestClientRetryIntegration:
    async def test_transient_5xx_is_retried(
        self, make_client: Callable[[Handler], object]
    ) -> None:
        attempts = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                return httpx.Response(503, text="starting up")
            return httpx.Response(200, json={"data": {"ok": True}})

        from app.config import Settings
        from app.integrations.datahub import DataHubClient, GraphQLClient

        settings = Settings(
            datahub_gms_url="http://datahub.test:8080",
            datahub_max_retries=3,
            datahub_retry_base_delay_seconds=0.0,
            datahub_retry_max_delay_seconds=0.0,
        )
        client = DataHubClient(
            settings=settings, transport=httpx.MockTransport(handler)
        )
        data = await GraphQLClient(client).execute("{ ok }")

        assert data == {"ok": True}
        # GMS answers 503 while booting; that is exactly when a retry helps.
        assert attempts == 3

    async def test_401_is_not_retried(self) -> None:
        attempts = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(401)

        from app.config import Settings
        from app.integrations.datahub import DataHubClient, GraphQLClient

        settings = Settings(
            datahub_max_retries=5,
            datahub_retry_base_delay_seconds=0.0,
            datahub_retry_max_delay_seconds=0.0,
        )
        client = DataHubClient(
            settings=settings, transport=httpx.MockTransport(handler)
        )
        with pytest.raises(DataHubAuthenticationError):
            await GraphQLClient(client).execute("{ ok }")
        assert attempts == 1


class TestTTLCache:
    async def test_second_call_is_served_from_cache(self) -> None:
        cache = TTLCache(ttl_seconds=60.0)
        calls = 0

        async def factory() -> str:
            nonlocal calls
            calls += 1
            return "value"

        assert await cache.get_or_load("k", factory) == "value"
        assert await cache.get_or_load("k", factory) == "value"
        assert calls == 1
        assert cache.stats().hits == 1
        assert cache.stats().misses == 1

    async def test_failures_are_never_cached(self) -> None:
        # The property that matters most: a DataHub blip must not be pinned
        # in place for the whole TTL.
        cache = TTLCache(ttl_seconds=60.0)
        calls = 0

        async def failing() -> str:
            nonlocal calls
            calls += 1
            raise DataHubConnectionError("refused")

        for _ in range(3):
            with pytest.raises(DataHubConnectionError):
                await cache.get_or_load("k", failing)

        # Every call reached the factory; nothing was stored.
        assert calls == 3
        assert cache.stats().entries == 0

    async def test_recovers_immediately_after_a_failure(self) -> None:
        cache = TTLCache(ttl_seconds=60.0)
        state = {"fail": True}

        async def flaky() -> str:
            if state["fail"]:
                raise DataHubConnectionError("refused")
            return "recovered"

        with pytest.raises(DataHubConnectionError):
            await cache.get_or_load("k", flaky)

        state["fail"] = False
        # No stale error entry blocking the retry.
        assert await cache.get_or_load("k", flaky) == "recovered"

    async def test_entries_expire(self) -> None:
        cache = TTLCache(ttl_seconds=0.05)
        calls = 0

        async def factory() -> str:
            nonlocal calls
            calls += 1
            return "value"

        await cache.get_or_load("k", factory)
        await asyncio.sleep(0.1)
        await cache.get_or_load("k", factory)
        assert calls == 2

    async def test_concurrent_misses_collapse_into_one_call(self) -> None:
        # Single-flight: without this, a cold cache under load stampedes GMS.
        cache = TTLCache(ttl_seconds=60.0)
        calls = 0

        async def slow_factory() -> str:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.05)
            return "value"

        results = await asyncio.gather(
            *[cache.get_or_load("same-key", slow_factory) for _ in range(10)]
        )
        assert results == ["value"] * 10
        assert calls == 1

    async def test_lru_eviction_bounds_memory(self) -> None:
        cache = TTLCache(ttl_seconds=60.0, max_entries=3)

        async def factory_for(value: str) -> str:
            return value

        for i in range(5):
            await cache.get_or_load(f"k{i}", lambda i=i: factory_for(f"v{i}"))

        stats = cache.stats()
        assert stats.entries == 3
        assert stats.evictions == 2

    async def test_null_cache_never_stores(self) -> None:
        cache = NullCache()
        calls = 0

        async def factory() -> str:
            nonlocal calls
            calls += 1
            return "value"

        await cache.get_or_load("k", factory)
        await cache.get_or_load("k", factory)
        assert calls == 2

    def test_cache_keys_are_order_independent(self) -> None:
        assert build_cache_key("op", a=1, b=2) == build_cache_key("op", b=2, a=1)
        assert build_cache_key("op", a=1) != build_cache_key("op", a=2)
        # Types must not collide: 1 and "1" are different cache entries.
        assert build_cache_key("op", a=1) != build_cache_key("op", a="1")


class TestServiceCaching:
    async def test_repeated_dataset_list_hits_datahub_once(
        self, make_service: Callable[[Handler], DataHubService], make_client
    ) -> None:
        requests = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal requests
            requests += 1
            return httpx.Response(
                200,
                json={
                    "data": fixtures.search_response(fixtures.DATASET_COMPLETE, total=1)
                },
            )

        from app.config import Settings
        from app.integrations.datahub import DataHubClient, GraphQLClient

        settings = Settings(datahub_gms_url="http://datahub.test:8080")
        client = DataHubClient(
            settings=settings, transport=httpx.MockTransport(handler)
        )
        service = DataHubService(
            graphql=GraphQLClient(client),
            client=client,
            settings=settings,
            cache=TTLCache(ttl_seconds=60.0),
        )

        first = await service.get_datasets()
        second = await service.get_datasets()

        assert first.total == second.total == 1
        assert requests == 1
        assert service.cache_stats.hits == 1

    async def test_different_pages_are_cached_separately(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        requests = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal requests
            requests += 1
            return httpx.Response(200, json={"data": fixtures.search_response(total=0)})

        from app.config import Settings
        from app.integrations.datahub import DataHubClient, GraphQLClient

        settings = Settings(datahub_gms_url="http://datahub.test:8080")
        client = DataHubClient(
            settings=settings, transport=httpx.MockTransport(handler)
        )
        service = DataHubService(
            graphql=GraphQLClient(client),
            client=client,
            settings=settings,
            cache=TTLCache(ttl_seconds=60.0),
        )

        await service.get_datasets(start=0)
        await service.get_datasets(start=20)
        assert requests == 2

    async def test_service_errors_are_not_cached(
        self, make_service: Callable[[Handler], DataHubService]
    ) -> None:
        requests = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal requests
            requests += 1
            return httpx.Response(200, json={"errors": [{"message": "boom"}]})

        from app.config import Settings
        from app.integrations.datahub import DataHubClient, GraphQLClient

        settings = Settings(datahub_gms_url="http://datahub.test:8080")
        client = DataHubClient(
            settings=settings, transport=httpx.MockTransport(handler)
        )
        service = DataHubService(
            graphql=GraphQLClient(client),
            client=client,
            settings=settings,
            cache=TTLCache(ttl_seconds=60.0),
        )

        for _ in range(2):
            with pytest.raises(DataHubQueryError):
                await service.get_datasets()
        assert requests == 2
