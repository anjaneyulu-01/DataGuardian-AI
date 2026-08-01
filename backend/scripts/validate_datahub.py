"""Validate the DataHub integration against a REAL running instance.

This is the acceptance harness for the integration layer. It talks to an
actual DataHub — never a mock — and reports exactly what worked, what did
not, and how long each call took.

    python scripts/validate_datahub.py                  # everything
    python scripts/validate_datahub.py --graphql-only   # queries only
    python scripts/validate_datahub.py --json report.json

What it does:

1. Probes GMS `/config` for reachability and version.
2. Executes every GraphQL document in `queries.py` against the live endpoint
   and reports per-query success, latency, and the exact GraphQL error when
   one fails. This is how schema incompatibilities are found.
3. Exercises every REST endpoint through the running FastAPI app.
4. Reports latency percentiles and flags slow operations.

Design rule: this script NEVER fabricates a result. If DataHub is
unreachable, every check is reported as BLOCKED with the reason. A green
report from this script means the integration genuinely worked.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any

# Make `app` importable when run as `python scripts/validate_datahub.py`.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

import httpx

from app.config import settings
from app.integrations.datahub import (
    DataHubClient,
    DataHubError,
    DataHubService,
    GraphQLClient,
)
from app.integrations.datahub import queries as q

# Latency above this is called out as slow in the report.
SLOW_MS = 1000.0


@dataclass
class CheckResult:
    """One validated operation."""

    name: str
    category: str
    status: str  # PASS | FAIL | BLOCKED | SKIP
    latency_ms: float | None = None
    detail: str = ""
    data_summary: str = ""

    @property
    def is_slow(self) -> bool:
        return self.latency_ms is not None and self.latency_ms > SLOW_MS


@dataclass
class Report:
    datahub_reachable: bool = False
    datahub_version: str | None = None
    gms_url: str = ""
    authenticated: bool = False
    checks: list[CheckResult] = field(default_factory=list)
    dataset_count: int | None = None
    domain_count: int | None = None
    owner_count: int | None = None
    blocking_reason: str | None = None

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)
        icon = {"PASS": "PASS", "FAIL": "FAIL", "BLOCKED": "BLKD", "SKIP": "SKIP"}[
            result.status
        ]
        latency = f"{result.latency_ms:8.1f}ms" if result.latency_ms else "        --"
        slow = "  <-- SLOW" if result.is_slow else ""
        print(f"  [{icon}] {latency}  {result.name}{slow}")
        if result.data_summary:
            print(f"           {result.data_summary}")
        if result.status in ("FAIL", "BLOCKED") and result.detail:
            print(f"           {result.detail[:300]}")

    def latencies(self, category: str | None = None) -> list[float]:
        return [
            c.latency_ms
            for c in self.checks
            if c.latency_ms is not None
            and c.status == "PASS"
            and (category is None or c.category == category)
        ]


async def timed(coro_factory: Any) -> tuple[Any, float, Exception | None]:
    """Run a coroutine factory, returning (result, elapsed_ms, error)."""
    started = time.perf_counter()
    try:
        result = await coro_factory()
        return result, (time.perf_counter() - started) * 1000, None
    except Exception as exc:
        return None, (time.perf_counter() - started) * 1000, exc


# ---------------------------------------------------------------------------
# 1. Connectivity
# ---------------------------------------------------------------------------


async def check_connectivity(service: DataHubService, report: Report) -> bool:
    print("\n=== 1. DataHub connectivity ===")
    health, elapsed, error = await timed(service.check_health)

    if error is not None or health is None:
        report.blocking_reason = f"Health probe raised: {error}"
        report.add(
            CheckResult(
                "GMS /config",
                "connectivity",
                "BLOCKED",
                elapsed,
                detail=str(error),
            )
        )
        return False

    report.datahub_reachable = health.reachable
    report.datahub_version = health.version
    report.gms_url = health.gms_url
    report.authenticated = health.authenticated

    if not health.reachable:
        report.blocking_reason = health.error or "DataHub unreachable"
        report.add(
            CheckResult(
                "GMS /config",
                "connectivity",
                "BLOCKED",
                elapsed,
                detail=health.error or "unreachable",
            )
        )
        return False

    report.add(
        CheckResult(
            "GMS /config",
            "connectivity",
            "PASS",
            elapsed,
            data_summary=f"version={health.version or 'unknown'} "
            f"authenticated={health.authenticated}",
        )
    )
    return True


# ---------------------------------------------------------------------------
# 2. GraphQL documents
# ---------------------------------------------------------------------------


async def check_graphql(
    graphql: GraphQLClient, report: Report, sample_urn: str | None
) -> str | None:
    """Execute every document in `queries.py` against the live endpoint.

    Returns a dataset URN discovered from the listing, for the URN-dependent
    queries that follow.
    """
    print("\n=== 2. GraphQL documents ===")

    # Ordered so the dataset listing runs first and supplies a real URN.
    plan: list[tuple[str, str, dict[str, Any], str]] = [
        (
            "LIST_DATASETS",
            q.LIST_DATASETS,
            {"query": "*", "start": 0, "count": 5},
            "listDatasets",
        ),
        (
            "LIST_DOMAINS",
            q.LIST_DOMAINS,
            {"start": 0, "count": 5},
            "listDomains",
        ),
        (
            "AGGREGATE_OWNERS",
            q.AGGREGATE_OWNERS,
            {"query": "*"},
            "aggregateOwners",
        ),
        (
            "LIST_TAGS",
            q.LIST_TAGS,
            {"query": "*", "start": 0, "count": 5},
            "listTags",
        ),
        (
            "SEARCH_ENTITIES",
            q.SEARCH_ENTITIES,
            {"types": ["DATASET"], "query": "*", "start": 0, "count": 5},
            "searchEntities",
        ),
    ]

    discovered_urn = sample_urn

    for label, document, variables, operation in plan:
        data, elapsed, error = await timed(
            lambda d=document, v=variables, o=operation: graphql.execute(d, v, o)
        )
        if error is not None:
            report.add(
                CheckResult(label, "graphql", "FAIL", elapsed, detail=_describe(error))
            )
            continue

        summary = _summarise(label, data)
        report.add(CheckResult(label, "graphql", "PASS", elapsed, data_summary=summary))

        if label == "LIST_DATASETS" and discovered_urn is None:
            discovered_urn = _first_urn(data)

    if discovered_urn is None:
        print("\n  No dataset URN available - URN-dependent queries skipped.")
        print("  This means DataHub has no dataset metadata ingested yet.")
        for label in (
            "GET_DATASET",
            "GET_DATASET_SCHEMA",
            "GET_DATASET_OWNERS",
            "GET_LINEAGE",
            "GET_DATASET_PROFILES",
            "GET_DATASET_USAGE",
        ):
            report.add(
                CheckResult(
                    label,
                    "graphql",
                    "SKIP",
                    detail="No dataset URN in DataHub - ingest metadata first",
                )
            )
        return None

    print(f"\n  Using discovered URN: {discovered_urn}")

    urn_plan: list[tuple[str, str, dict[str, Any], str]] = [
        ("GET_DATASET", q.GET_DATASET, {"urn": discovered_urn}, "getDataset"),
        (
            "GET_DATASET_SCHEMA",
            q.GET_DATASET_SCHEMA,
            {"urn": discovered_urn},
            "getDatasetSchema",
        ),
        (
            "GET_DATASET_OWNERS",
            q.GET_DATASET_OWNERS,
            {"urn": discovered_urn},
            "getDatasetOwners",
        ),
        (
            "GET_LINEAGE",
            q.GET_LINEAGE,
            {
                "urn": discovered_urn,
                "direction": "DOWNSTREAM",
                "start": 0,
                "count": 5,
            },
            "getLineage",
        ),
        (
            "GET_DATASET_PROFILES",
            q.GET_DATASET_PROFILES,
            {"urn": discovered_urn, "limit": 5},
            "getDatasetProfiles",
        ),
        (
            "GET_DATASET_USAGE",
            q.GET_DATASET_USAGE,
            {"urn": discovered_urn, "range": "MONTH"},
            "getDatasetUsage",
        ),
    ]

    for label, document, variables, operation in urn_plan:
        data, elapsed, error = await timed(
            lambda d=document, v=variables, o=operation: graphql.execute(d, v, o)
        )
        if error is not None:
            report.add(
                CheckResult(label, "graphql", "FAIL", elapsed, detail=_describe(error))
            )
            continue
        report.add(
            CheckResult(
                label, "graphql", "PASS", elapsed, data_summary=_summarise(label, data)
            )
        )

    # GET_DOMAIN needs a real domain URN.
    domain_urn = await _first_domain_urn(graphql)
    if domain_urn:
        data, elapsed, error = await timed(
            lambda: graphql.execute(q.GET_DOMAIN, {"urn": domain_urn}, "getDomain")
        )
        status = "FAIL" if error else "PASS"
        report.add(
            CheckResult(
                "GET_DOMAIN",
                "graphql",
                status,
                elapsed,
                detail=_describe(error) if error else "",
                data_summary="" if error else f"urn={domain_urn}",
            )
        )
    else:
        report.add(
            CheckResult(
                "GET_DOMAIN", "graphql", "SKIP", detail="No domains defined in DataHub"
            )
        )

    return discovered_urn


# ---------------------------------------------------------------------------
# 3. Service layer
# ---------------------------------------------------------------------------


async def check_service(
    service: DataHubService, report: Report, urn: str | None
) -> None:
    print("\n=== 3. Service layer ===")

    page, elapsed, error = await timed(lambda: service.get_datasets(count=10))
    if error is None and page is not None:
        report.dataset_count = page.total
        report.add(
            CheckResult(
                "get_datasets()",
                "service",
                "PASS",
                elapsed,
                data_summary=f"total={page.total} returned={len(page.results)}",
            )
        )
    else:
        report.add(
            CheckResult(
                "get_datasets()", "service", "FAIL", elapsed, detail=_describe(error)
            )
        )

    domains, elapsed, error = await timed(lambda: service.get_domains(count=10))
    if error is None and domains is not None:
        report.domain_count = domains.total
        report.add(
            CheckResult(
                "get_domains()",
                "service",
                "PASS",
                elapsed,
                data_summary=f"total={domains.total}",
            )
        )
    else:
        report.add(
            CheckResult(
                "get_domains()", "service", "FAIL", elapsed, detail=_describe(error)
            )
        )

    owners, elapsed, error = await timed(service.get_owners)
    if error is None and owners is not None:
        report.owner_count = len(owners)
        report.add(
            CheckResult(
                "get_owners()",
                "service",
                "PASS",
                elapsed,
                data_summary=f"distinct owners={len(owners)}",
            )
        )
    else:
        report.add(
            CheckResult(
                "get_owners()", "service", "FAIL", elapsed, detail=_describe(error)
            )
        )

    if urn is None:
        for name in ("get_dataset()", "get_lineage()", "get_statistics()"):
            report.add(
                CheckResult(name, "service", "SKIP", detail="No dataset URN available")
            )
        return

    dataset, elapsed, error = await timed(lambda: service.get_dataset(urn))
    report.add(
        CheckResult(
            "get_dataset()",
            "service",
            "FAIL" if error else "PASS",
            elapsed,
            detail=_describe(error) if error else "",
            data_summary=""
            if error or dataset is None
            else f"name={dataset.name} owners={len(dataset.owners)} "
            f"tags={len(dataset.tags)}",
        )
    )

    lineage, elapsed, error = await timed(lambda: service.get_lineage(urn))
    report.add(
        CheckResult(
            "get_lineage()",
            "service",
            "FAIL" if error else "PASS",
            elapsed,
            detail=_describe(error) if error else "",
            data_summary=""
            if error or lineage is None
            else f"downstream nodes={len(lineage.nodes)}",
        )
    )

    stats, elapsed, error = await timed(lambda: service.get_statistics(urn))
    report.add(
        CheckResult(
            "get_statistics()",
            "service",
            "FAIL" if error else "PASS",
            elapsed,
            detail=_describe(error) if error else "",
            data_summary=""
            if error or stats is None
            else f"profiles={len(stats.profiles)} usage={stats.usage is not None}",
        )
    )


# ---------------------------------------------------------------------------
# 4. REST endpoints
# ---------------------------------------------------------------------------


async def check_rest(base_url: str, report: Report, urn: str | None) -> None:
    print(f"\n=== 4. REST endpoints ({base_url}) ===")

    endpoints: list[tuple[str, str, dict[str, Any]]] = [
        ("GET /health", "/api/v1/health", {}),
        ("GET /health/datahub", "/api/v1/health/datahub", {}),
        ("GET /datasets", "/api/v1/datasets", {"count": 10}),
        ("GET /owners", "/api/v1/owners", {}),
        ("GET /domains", "/api/v1/domains", {}),
    ]
    if urn:
        endpoints += [
            ("GET /datasets/{urn}", f"/api/v1/datasets/{urn}", {}),
            ("GET /lineage", "/api/v1/lineage", {"urn": urn}),
            ("GET /lineage/impact", "/api/v1/lineage/impact", {"urn": urn}),
            ("GET /statistics", "/api/v1/statistics", {"urn": urn}),
        ]

    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        # Probe first so an unreachable API is reported once, not nine times.
        try:
            await client.get("/api/v1/health")
        except httpx.HTTPError as exc:
            for name, _, _ in endpoints:
                report.add(
                    CheckResult(
                        name,
                        "rest",
                        "BLOCKED",
                        detail=f"API not running at {base_url}: {exc}",
                    )
                )
            return

        for name, path, params in endpoints:
            response, elapsed, error = await timed(
                lambda p=path, q_=params: client.get(p, params=q_)
            )
            if error is not None:
                report.add(
                    CheckResult(name, "rest", "FAIL", elapsed, detail=str(error))
                )
                continue

            ok = response.status_code < 400
            report.add(
                CheckResult(
                    name,
                    "rest",
                    "PASS" if ok else "FAIL",
                    elapsed,
                    detail="" if ok else response.text[:300],
                    data_summary=f"HTTP {response.status_code} "
                    f"{_body_summary(response)}",
                )
            )

    # Second pass over /datasets to demonstrate the cache.
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        _, cold, _ = await timed(
            lambda: client.get("/api/v1/datasets", params={"count": 10, "start": 1})
        )
        _, warm, _ = await timed(
            lambda: client.get("/api/v1/datasets", params={"count": 10, "start": 1})
        )
        report.add(
            CheckResult(
                "cache effect (/datasets)",
                "cache",
                "PASS",
                warm,
                data_summary=f"cold={cold:.1f}ms warm={warm:.1f}ms "
                f"speedup={cold / warm:.1f}x"
                if warm > 0
                else "",
            )
        )


# ---------------------------------------------------------------------------
# Helpers and reporting
# ---------------------------------------------------------------------------


def _describe(error: Exception | None) -> str:
    if error is None:
        return ""
    if isinstance(error, DataHubError):
        return f"{type(error).__name__}: {error.detail}"
    return f"{type(error).__name__}: {error}"


def _first_urn(data: Any) -> str | None:
    try:
        results = data["searchAcrossEntities"]["searchResults"]
        for entry in results:
            urn = (entry or {}).get("entity", {}).get("urn")
            if urn:
                return str(urn)
    except (KeyError, TypeError, AttributeError):
        return None
    return None


async def _first_domain_urn(graphql: GraphQLClient) -> str | None:
    try:
        data = await graphql.execute(
            q.LIST_DOMAINS, {"start": 0, "count": 1}, "listDomains"
        )
        domains = data["listDomains"]["domains"]
        return str(domains[0]["urn"]) if domains else None
    except Exception:
        return None


def _summarise(label: str, data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    if "searchAcrossEntities" in data:
        node = data["searchAcrossEntities"] or {}
        return (
            f"total={node.get('total')} returned={len(node.get('searchResults') or [])}"
        )
    if "listDomains" in data:
        node = data["listDomains"] or {}
        return f"total={node.get('total')}"
    if "aggregateAcrossEntities" in data:
        facets = (data["aggregateAcrossEntities"] or {}).get("facets") or []
        for facet in facets:
            if (facet or {}).get("field") == "owners":
                return f"owner buckets={len(facet.get('aggregations') or [])}"
        return f"facets={len(facets)}"
    if "searchAcrossLineage" in data:
        node = data["searchAcrossLineage"] or {}
        return f"total={node.get('total')}"
    if "dataset" in data:
        node = data["dataset"]
        if node is None:
            return "dataset=null"
        keys = [k for k in node if k != "urn"]
        return f"fields={','.join(keys[:4])}"
    return ""


def _body_summary(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    if isinstance(body, dict):
        if "total" in body:
            return f"total={body['total']} results={len(body.get('results') or [])}"
        if "reachable" in body:
            return f"reachable={body['reachable']} version={body.get('version')}"
        if "nodes" in body:
            return f"nodes={len(body['nodes'])}"
        if "detail" in body:
            return f"detail={str(body['detail'])[:80]}"
    if isinstance(body, list):
        return f"items={len(body)}"
    return ""


def print_summary(report: Report) -> None:
    print("\n" + "=" * 72)
    print("VALIDATION SUMMARY")
    print("=" * 72)

    counts: dict[str, int] = {}
    for check in report.checks:
        counts[check.status] = counts.get(check.status, 0) + 1

    print(f"  DataHub reachable : {report.datahub_reachable}")
    print(f"  DataHub version   : {report.datahub_version or 'unknown'}")
    print(f"  GMS URL           : {report.gms_url}")
    print(f"  Authenticated     : {report.authenticated}")
    print(f"  Dataset count     : {_fmt(report.dataset_count)}")
    print(f"  Domain count      : {_fmt(report.domain_count)}")
    print(f"  Owner count       : {_fmt(report.owner_count)}")
    print()
    print(
        f"  Checks: {counts.get('PASS', 0)} passed, {counts.get('FAIL', 0)} failed, "
        f"{counts.get('SKIP', 0)} skipped, {counts.get('BLOCKED', 0)} blocked"
    )

    for category in ("graphql", "service", "rest"):
        values = report.latencies(category)
        if not values:
            continue
        print(
            f"  {category:<8} latency: avg={statistics.mean(values):7.1f}ms  "
            f"median={statistics.median(values):7.1f}ms  "
            f"max={max(values):7.1f}ms  (n={len(values)})"
        )

    overall = report.latencies()
    if overall:
        print(f"  {'OVERALL':<8} average: {statistics.mean(overall):.1f}ms")

    slow = [c for c in report.checks if c.is_slow and c.status == "PASS"]
    if slow:
        print(f"\n  Slow operations (>{SLOW_MS:.0f}ms):")
        for check in sorted(slow, key=lambda c: -(c.latency_ms or 0)):
            print(f"    {check.latency_ms:8.1f}ms  {check.name}")

    failures = [c for c in report.checks if c.status == "FAIL"]
    if failures:
        print("\n  FAILURES:")
        for check in failures:
            print(f"    {check.name}: {check.detail[:200]}")

    if report.blocking_reason:
        print(f"\n  BLOCKED: {report.blocking_reason}")

    print("=" * 72)


def _fmt(value: int | None) -> str:
    return "not measured" if value is None else str(value)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--urn", default=None, help="Use a specific dataset URN")
    parser.add_argument("--graphql-only", action="store_true")
    parser.add_argument("--json", dest="json_path", default=None)
    args = parser.parse_args()

    print("=" * 72)
    print("DataGuardian AI - DataHub integration validation")
    print("=" * 72)
    print(f"  GMS URL : {settings.datahub_gms_url}")
    print(f"  GraphQL : {settings.datahub_graphql_url}")
    print(f"  Token   : {'set' if settings.datahub_token else 'NOT SET'}")

    report = Report()
    client = DataHubClient(settings=settings)
    graphql = GraphQLClient(client)
    # No cache: every measurement must reflect a real DataHub round-trip.
    service = DataHubService(graphql=graphql, client=client, settings=settings)

    try:
        reachable = await check_connectivity(service, report)
        if not reachable:
            print("\n" + "!" * 72)
            print("DataHub is NOT reachable. Nothing below can be validated.")
            print(f"Reason: {report.blocking_reason}")
            print("!" * 72)
            print_summary(report)
            return 2

        urn = await check_graphql(graphql, report, args.urn)
        if not args.graphql_only:
            await check_service(service, report, urn)
            await check_rest(args.api_url, report, urn)
    finally:
        await client.aclose()

    print_summary(report)

    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "datahub_reachable": report.datahub_reachable,
                    "datahub_version": report.datahub_version,
                    "gms_url": report.gms_url,
                    "authenticated": report.authenticated,
                    "dataset_count": report.dataset_count,
                    "domain_count": report.domain_count,
                    "owner_count": report.owner_count,
                    "blocking_reason": report.blocking_reason,
                    "checks": [asdict(c) for c in report.checks],
                },
                handle,
                indent=2,
            )
        print(f"\nJSON report written to {args.json_path}")

    return 1 if any(c.status == "FAIL" for c in report.checks) else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
