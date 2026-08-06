"""Shared FastAPI dependencies.

This is the seam between the framework and the integration layer. Routers
declare what they need as an annotated dependency and never construct a
client, so the same `DataHubService` can be driven by HTTP today and by the
scheduler or the agent tomorrow without duplicating wiring.

The DataHub client is created once in the application lifespan and stored on
`app.state`. Building one per request would throw away the connection pool
and re-run the TLS handshake on every call.
"""

from typing import Annotated

from fastapi import Depends, Query, Request

from app.agents import GovernanceAgent
from app.config import Settings, get_settings
from app.integrations.datahub import DataHubClient, DataHubService, GraphQLClient
from app.integrations.datahub.cache import NullCache, TTLCache
from app.llm import BaseLLM, LLMFactory
from app.tools import DataHubToolkit, build_tools

# Keys under which the lifespan stores shared, process-wide objects on
# `app.state`. All must outlive a single request: the clients for their
# connection pools, the cache so entries survive between calls.
DATAHUB_CLIENT_STATE_KEY = "datahub_client"
DATAHUB_CACHE_STATE_KEY = "datahub_cache"
LLM_PROVIDER_STATE_KEY = "llm_provider"


def get_app_settings() -> Settings:
    """Expose configuration as a dependency so tests can override it."""
    return get_settings()


def get_datahub_client(request: Request) -> DataHubClient:
    """Return the process-wide DataHub client created by the lifespan."""
    client = getattr(request.app.state, DATAHUB_CLIENT_STATE_KEY, None)
    if client is None:
        # Only reachable if the app was constructed without its lifespan,
        # which in practice means a misconfigured test.
        raise RuntimeError(
            "DataHub client is not initialised. It is created in the "
            "application lifespan; ensure the app is started with one."
        )
    return client


def get_datahub_cache(request: Request) -> TTLCache:
    """Return the process-wide metadata cache.

    Falls back to a `NullCache` when the lifespan did not install one, so a
    missing cache degrades to "no caching" rather than breaking the request.
    """
    cache = getattr(request.app.state, DATAHUB_CACHE_STATE_KEY, None)
    return cache if isinstance(cache, TTLCache) else NullCache()


def get_datahub_service(
    client: Annotated[DataHubClient, Depends(get_datahub_client)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    cache: Annotated[TTLCache, Depends(get_datahub_cache)],
) -> DataHubService:
    """Assemble the service from the shared client and cache.

    `GraphQLClient` and `DataHubService` are cheap stateless wrappers around
    the pooled transport, so building them per request costs nothing and keeps
    each request's dependency graph explicit. The client and cache are the
    only long-lived pieces, and both come from `app.state`.
    """
    return DataHubService(
        graphql=GraphQLClient(client),
        client=client,
        settings=settings,
        cache=cache,
    )


def get_llm(request: Request) -> BaseLLM:
    """Return the process-wide LLM provider created by the lifespan.

    Falls back to building one on demand rather than failing: an app started
    without its lifespan (some test setups) should still be able to reach the
    provider, and construction performs no I/O.
    """
    provider = getattr(request.app.state, LLM_PROVIDER_STATE_KEY, None)
    if isinstance(provider, BaseLLM):
        return provider
    return LLMFactory.create(get_settings())


def get_toolkit(
    service: Annotated[DataHubService, Depends(get_datahub_service)],
) -> DataHubToolkit:
    """Build the agent-facing toolkit over the shared service.

    All tools share one service, so they share its cache and connection pool:
    an agent run making five tool calls does not open five conversations with
    DataHub.
    """
    return build_tools(service)


def get_governance_agent(
    toolkit: Annotated[DataHubToolkit, Depends(get_toolkit)],
    llm: Annotated[BaseLLM, Depends(get_llm)],
) -> GovernanceAgent:
    """Assemble the governance agent for this request.

    The agent compiles its graph on construction — cheap (topology validation,
    no I/O) but not free, so if agent traffic grows this is the thing to hoist
    into the lifespan alongside the client and cache. Per-request today keeps
    the dependency graph explicit and the toolkit request-scoped.
    """
    return GovernanceAgent(toolkit=toolkit, llm=llm)


# --- Reusable annotated dependencies ---------------------------------------
# Routers import these instead of repeating `Depends(...)`.

SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DataHubClientDep = Annotated[DataHubClient, Depends(get_datahub_client)]
DataHubCacheDep = Annotated[TTLCache, Depends(get_datahub_cache)]
DataHubServiceDep = Annotated[DataHubService, Depends(get_datahub_service)]
LLMDep = Annotated[BaseLLM, Depends(get_llm)]
DataHubToolkitDep = Annotated[DataHubToolkit, Depends(get_toolkit)]
GovernanceAgentDep = Annotated[GovernanceAgent, Depends(get_governance_agent)]


# --- Common query parameters ------------------------------------------------
# Declared once so every paginated endpoint documents and validates
# pagination identically. The service clamps again, defensively.

StartQuery = Annotated[
    int, Query(ge=0, description="Zero-based offset into the result set.")
]
CountQuery = Annotated[
    int | None,
    Query(
        ge=1,
        le=200,
        description=(
            "Page size. Clamped server-side to DATAHUB_MAX_PAGE_SIZE when larger."
        ),
    ),
]
UrnQuery = Annotated[
    str,
    Query(
        min_length=1,
        description="DataHub entity URN, for example "
        "`urn:li:dataset:(urn:li:dataPlatform:hive,my_table,PROD)`.",
    ),
]
SearchQuery = Annotated[
    str,
    Query(description="DataHub search syntax. `*` matches everything."),
]
