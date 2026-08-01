"""The DataHub integration's public interface.

`DataHubService` is the single entry point everything else uses: the API
routers today, the governance rule engine and the LangGraph agent tomorrow.
Callers depend on this class and on `models.py` — never on GraphQL documents,
HTTP details, or raw dictionaries.

Responsibilities:

* Choose the query, pass validated variables, and map the result.
* Enforce pagination limits so no caller can ask GMS for an unbounded page.
* Decide what counts as an error. A dataset that does not exist raises; a
  dataset with no lineage returns an empty graph. That distinction is the
  reason this layer exists rather than callers talking to `graphql.py`.

The class takes a `GraphQLClient` rather than constructing one, so tests
inject a fake transport and no production wiring is duplicated here.
"""

import logging
import time
from typing import Any

from app.config import Settings
from app.config import settings as default_settings
from app.integrations.datahub import mapper, queries
from app.integrations.datahub.cache import (
    CacheStats,
    NullCache,
    TTLCache,
    build_cache_key,
)
from app.integrations.datahub.client import DataHubClient
from app.integrations.datahub.exceptions import (
    DataHubEntityNotFoundError,
    DataHubError,
)
from app.integrations.datahub.graphql import GraphQLClient
from app.integrations.datahub.models import (
    DataHubHealth,
    Dataset,
    DatasetSchema,
    DatasetStatistics,
    DatasetSummary,
    Domain,
    Lineage,
    LineageDirection,
    Owner,
    Page,
    Tag,
    TimeRange,
)

logger = logging.getLogger(__name__)

# DataHub's search syntax for "everything".
_MATCH_ALL = "*"

# GMS exposes its build info here, unauthenticated. Used as the connectivity
# probe because it is cheap and does not depend on any metadata existing.
_CONFIG_PATH = "/config"


class DataHubService:
    """Read operations against DataHub metadata."""

    def __init__(
        self,
        graphql: GraphQLClient,
        client: DataHubClient,
        settings: Settings | None = None,
        cache: TTLCache | None = None,
    ) -> None:
        self._graphql = graphql
        self._client = client
        self._settings = settings or default_settings
        # A NullCache rather than None, so the cached and uncached code paths
        # are identical and cannot drift apart.
        self._cache = cache if cache is not None else NullCache()

    @property
    def cache_stats(self) -> CacheStats:
        """Cache counters, surfaced on the health endpoint."""
        return self._cache.stats()

    # -- Health ---------------------------------------------------------------

    async def check_health(self) -> DataHubHealth:
        """Probe DataHub connectivity.

        Never raises. An unreachable DataHub is a *reportable state*, not an
        error: a monitoring endpoint that 502s tells an operator far less than
        one that says "unreachable, connection refused, here is the URL I
        tried". Callers that need failure semantics use the other methods.
        """
        started = time.perf_counter()
        try:
            # retry=False: the probe reports state, it does not do work. With
            # retries it would block ~7s on a down DataHub before answering.
            response = await self._client.get(_CONFIG_PATH, retry=False)
            latency_ms = (time.perf_counter() - started) * 1000

            if response.status_code >= 400:
                return mapper.map_health(
                    gms_url=self._client.base_url,
                    authenticated=self._client.is_authenticated,
                    reachable=False,
                    latency_ms=latency_ms,
                    error=(
                        f"GMS returned HTTP {response.status_code} from {_CONFIG_PATH}"
                    ),
                )

            try:
                config = response.json()
            except ValueError:
                # Something answered, but it is not DataHub — a stray dev
                # server on the same port is the usual cause.
                return mapper.map_health(
                    gms_url=self._client.base_url,
                    authenticated=self._client.is_authenticated,
                    reachable=False,
                    latency_ms=latency_ms,
                    error=(
                        f"{_CONFIG_PATH} did not return JSON; the configured "
                        "URL may not be a DataHub GMS instance"
                    ),
                )

            return mapper.map_health(
                gms_url=self._client.base_url,
                authenticated=self._client.is_authenticated,
                reachable=True,
                config_raw=config,
                latency_ms=latency_ms,
            )

        except DataHubError as exc:
            logger.warning("DataHub health probe failed: %s", exc.detail)
            return mapper.map_health(
                gms_url=self._client.base_url,
                authenticated=self._client.is_authenticated,
                reachable=False,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=exc.detail,
            )

    # -- Datasets -------------------------------------------------------------

    async def get_datasets(
        self,
        query: str = _MATCH_ALL,
        start: int = 0,
        count: int | None = None,
    ) -> Page[DatasetSummary]:
        """List datasets, newest search relevance first.

        Args:
            query: DataHub search syntax. `*` matches everything.
            start: Zero-based offset.
            count: Page size, clamped to `DATAHUB_MAX_PAGE_SIZE`.
        """
        start, count = self._paginate(start, count)
        key = build_cache_key(
            "datasets", query=query or _MATCH_ALL, start=start, count=count
        )

        async def load() -> Page[DatasetSummary]:
            data = await self._graphql.execute(
                queries.LIST_DATASETS,
                {"query": query or _MATCH_ALL, "start": start, "count": count},
                operation_name="listDatasets",
            )
            page_start, page_count, total, datasets = mapper.map_dataset_page(
                data.get("searchAcrossEntities")
            )
            return Page[DatasetSummary](
                start=page_start, count=page_count, total=total, results=datasets
            )

        return await self._cache.get_or_load(key, load)

    async def get_dataset(self, urn: str) -> Dataset:
        """Fetch one dataset in full.

        Raises:
            DataHubEntityNotFoundError: The URN does not resolve.
        """
        data = await self._graphql.execute(
            queries.GET_DATASET, {"urn": urn}, operation_name="getDataset"
        )
        dataset = mapper.map_dataset(data.get("dataset"))
        if dataset is None:
            # GraphQL answers 200 with `{"dataset": null}` for a URN that does
            # not exist, so the 404 has to be raised here.
            raise DataHubEntityNotFoundError(f"Dataset not found in DataHub: {urn}")
        return dataset

    async def get_dataset_schema(self, urn: str) -> DatasetSchema:
        """Fetch only a dataset's schema.

        Cheaper than `get_dataset` when a caller needs columns alone — schema
        drift detection will page through many datasets.
        """
        data = await self._graphql.execute(
            queries.GET_DATASET_SCHEMA, {"urn": urn}, operation_name="getDatasetSchema"
        )
        dataset = data.get("dataset")
        if dataset is None:
            raise DataHubEntityNotFoundError(f"Dataset not found in DataHub: {urn}")

        schema = mapper.map_schema(mapper.as_dict(dataset).get("schemaMetadata"))
        # A dataset with no schema aspect is legitimate (an unprofiled S3 path,
        # for example), so this returns an empty schema rather than raising.
        return schema or DatasetSchema()

    async def search(
        self,
        query: str,
        entity_types: list[str] | None = None,
        start: int = 0,
        count: int | None = None,
    ) -> Page[DatasetSummary]:
        """Free-text search.

        TODO(datahub): Only DATASET results are mapped today. When the agent
        needs dashboards or pipelines, extend `mapper.map_dataset_page` with
        the other entity types rather than adding a second search path here.
        """
        start, count = self._paginate(start, count)
        data = await self._graphql.execute(
            queries.SEARCH_ENTITIES,
            {
                "types": entity_types or ["DATASET"],
                "query": query or _MATCH_ALL,
                "start": start,
                "count": count,
            },
            operation_name="searchEntities",
        )
        page_start, page_count, total, datasets = mapper.map_dataset_page(
            data.get("searchAcrossEntities")
        )
        return Page[DatasetSummary](
            start=page_start, count=page_count, total=total, results=datasets
        )

    # -- Ownership ------------------------------------------------------------

    async def get_owners(
        self, dataset_urn: str | None = None, query: str = _MATCH_ALL
    ) -> list[Owner]:
        """List owners.

        With `dataset_urn`, returns that dataset's owners. Without it, returns
        every distinct owner across the catalogue with the number of datasets
        each one owns, via a search facet aggregation — far cheaper than
        paging every dataset and de-duplicating client-side.
        """
        key = build_cache_key("owners", dataset_urn=dataset_urn, query=query)

        async def load() -> list[Owner]:
            if dataset_urn:
                data = await self._graphql.execute(
                    queries.GET_DATASET_OWNERS,
                    {"urn": dataset_urn},
                    operation_name="getDatasetOwners",
                )
                dataset = data.get("dataset")
                if dataset is None:
                    raise DataHubEntityNotFoundError(
                        f"Dataset not found in DataHub: {dataset_urn}"
                    )
                return mapper.map_owners(mapper.as_dict(dataset).get("ownership"))

            data = await self._graphql.execute(
                queries.AGGREGATE_OWNERS,
                {"query": query or _MATCH_ALL},
                operation_name="aggregateOwners",
            )
            return mapper.map_owner_aggregations(data.get("aggregateAcrossEntities"))

        return await self._cache.get_or_load(key, load)

    # -- Domains --------------------------------------------------------------

    async def get_domains(
        self, start: int = 0, count: int | None = None
    ) -> Page[Domain]:
        """List domains with their owners and asset counts."""
        start, count = self._paginate(start, count)
        key = build_cache_key("domains", start=start, count=count)

        async def load() -> Page[Domain]:
            data = await self._graphql.execute(
                queries.LIST_DOMAINS,
                {"start": start, "count": count},
                operation_name="listDomains",
            )
            page_start, page_count, total, domains = mapper.map_domain_page(
                data.get("listDomains")
            )
            return Page[Domain](
                start=page_start, count=page_count, total=total, results=domains
            )

        return await self._cache.get_or_load(key, load)

    async def get_domain(self, urn: str) -> Domain:
        """Fetch one domain."""
        data = await self._graphql.execute(
            queries.GET_DOMAIN, {"urn": urn}, operation_name="getDomain"
        )
        domain = mapper.map_domain(data.get("domain"))
        if domain is None:
            raise DataHubEntityNotFoundError(f"Domain not found in DataHub: {urn}")
        return domain

    # -- Tags -----------------------------------------------------------------

    async def get_tags(
        self, query: str = _MATCH_ALL, start: int = 0, count: int | None = None
    ) -> Page[Tag]:
        """List tags defined in DataHub."""
        start, count = self._paginate(start, count)
        data = await self._graphql.execute(
            queries.LIST_TAGS,
            {"query": query or _MATCH_ALL, "start": start, "count": count},
            operation_name="listTags",
        )
        page_start, page_count, total, tags = mapper.map_tag_page(
            data.get("searchAcrossEntities")
        )
        return Page[Tag](start=page_start, count=page_count, total=total, results=tags)

    # -- Lineage --------------------------------------------------------------

    async def get_lineage(
        self,
        urn: str,
        direction: LineageDirection = LineageDirection.DOWNSTREAM,
        start: int = 0,
        count: int | None = None,
    ) -> Lineage:
        """Traverse lineage in one direction.

        An asset with no lineage returns a `Lineage` with zero nodes — that is
        a valid answer, not a 404. Only a URN that does not exist is an error,
        and DataHub reports that as a GraphQL error rather than an empty
        result.
        """
        start, count = self._paginate(start, count)
        data = await self._graphql.execute(
            queries.GET_LINEAGE,
            {
                "urn": urn,
                "direction": direction.value,
                "start": start,
                "count": count,
            },
            operation_name="getLineage",
        )
        return mapper.map_lineage(
            data.get("searchAcrossLineage"), urn=urn, direction=direction
        )

    async def get_lineage_both_directions(
        self, urn: str, count: int | None = None
    ) -> dict[str, Lineage]:
        """Fetch upstream and downstream lineage together.

        Convenience for impact analysis, which always needs both sides. Kept
        as two GraphQL calls because DataHub traverses each direction
        independently.
        """
        upstream = await self.get_lineage(urn, LineageDirection.UPSTREAM, count=count)
        downstream = await self.get_lineage(
            urn, LineageDirection.DOWNSTREAM, count=count
        )
        return {"upstream": upstream, "downstream": downstream}

    # -- Statistics -----------------------------------------------------------

    async def get_statistics(
        self,
        urn: str,
        time_range: TimeRange = TimeRange.MONTH,
        profile_limit: int = 10,
    ) -> DatasetStatistics:
        """Fetch profiling and usage statistics for a dataset.

        Profiles and usage come from different ingestion sources and are
        independently optional. Usage is the more fragile of the two — it needs
        a usage-ingestion source that most quickstart instances lack — so a
        usage failure is downgraded to `usage_unavailable_reason` instead of
        failing the whole call. A profile failure is *not* swallowed: if the
        core query breaks, the caller needs to know.
        """
        key = build_cache_key(
            "statistics",
            urn=urn,
            time_range=time_range.value,
            profile_limit=profile_limit,
        )

        async def load() -> DatasetStatistics:
            profiles_data = await self._graphql.execute(
                queries.GET_DATASET_PROFILES,
                {"urn": urn, "limit": max(1, profile_limit)},
                operation_name="getDatasetProfiles",
            )
            dataset = profiles_data.get("dataset")
            if dataset is None:
                raise DataHubEntityNotFoundError(f"Dataset not found in DataHub: {urn}")

            profiles_raw = mapper.as_dict(dataset).get("datasetProfiles")

            usage_raw: Any = None
            usage_error: str | None = None
            try:
                usage_data = await self._graphql.execute(
                    queries.GET_DATASET_USAGE,
                    {"urn": urn, "range": time_range.value},
                    operation_name="getDatasetUsage",
                )
                usage_raw = mapper.as_dict(usage_data.get("dataset")).get("usageStats")
            except DataHubError as exc:
                # Expected on instances without usage ingestion configured.
                # Downgraded, not raised — so this result is still cacheable.
                logger.info("Usage statistics unavailable for %s: %s", urn, exc.detail)
                usage_error = exc.detail

            return mapper.map_statistics(
                urn=urn,
                profiles_raw=profiles_raw,
                usage_raw=usage_raw,
                time_range=time_range,
                usage_unavailable_reason=usage_error,
            )

        return await self._cache.get_or_load(key, load)

    # -- Internals ------------------------------------------------------------

    def _paginate(self, start: int, count: int | None) -> tuple[int, int]:
        """Clamp pagination arguments to a safe range.

        Applied to every paginated call so a caller — or a confused agent —
        cannot ask GMS for a million rows in one request.
        """
        safe_start = max(0, start)
        requested = self._settings.datahub_default_page_size if count is None else count
        safe_count = max(1, min(requested, self._settings.datahub_max_page_size))
        return safe_start, safe_count
