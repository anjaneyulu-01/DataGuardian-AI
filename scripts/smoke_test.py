"""Post-deployment smoke test.

Verifies a live deployment end to end: the frontend serves, the backend is
healthy, the agent produces a grounded answer, and CORS is configured for the
frontend origin.

    # Local
    python scripts/smoke_test.py

    # Render
    python scripts/smoke_test.py \
        --api https://dataguardian-api.onrender.com \
        --web https://dataguardian-web.onrender.com

    python scripts/smoke_test.py --api ... --json report.json

Exit code is 0 only when every REQUIRED check passes, so this can gate a
release in CI.

Design rule, matching the rest of the project: this never fabricates a pass.
A dependency that is genuinely optional (DataHub, the LLM) is reported WARN,
not FAIL — the API is designed to run without them and degrade honestly. Only
things that make the deployment broken are FAIL.

Requires: httpx (already a backend dependency).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

# Render free-tier services spin down when idle and cold-start slowly, so the
# first request after a quiet period can legitimately take ~50 seconds.
COLD_START_TIMEOUT = 90.0
# An agent run calls a real LLM and may traverse several tools.
AGENT_TIMEOUT = 180.0
# Anything slower than this is called out, without failing the run.
SLOW_MS = 3000.0


@dataclass
class Check:
    name: str
    status: str  # PASS | FAIL | WARN | SKIP
    latency_ms: float | None = None
    detail: str = ""
    required: bool = True

    @property
    def is_slow(self) -> bool:
        return self.latency_ms is not None and self.latency_ms > SLOW_MS


@dataclass
class Report:
    api_url: str
    web_url: str | None
    checks: list[Check] = field(default_factory=list)

    def add(self, check: Check) -> Check:
        self.checks.append(check)
        icon = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN", "SKIP": "SKIP"}[
            check.status
        ]
        latency = f"{check.latency_ms:7.0f}ms" if check.latency_ms else "       --"
        slow = "  <-- SLOW" if check.is_slow else ""
        optional = "" if check.required else "  (optional)"
        print(f"  [{icon}] {latency}  {check.name}{slow}{optional}")
        if check.detail:
            print(f"          {check.detail}")
        return check

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if c.status == "FAIL" and c.required]

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if c.status == "WARN"]

    @property
    def ok(self) -> bool:
        return not self.failures


def timed(fn: Any) -> tuple[Any, float, Exception | None]:
    """Run `fn`, returning (result, elapsed_ms, error)."""
    started = time.perf_counter()
    try:
        return fn(), (time.perf_counter() - started) * 1000, None
    except Exception as exc:  # noqa: BLE001 - reporting, not handling
        return None, (time.perf_counter() - started) * 1000, exc


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_health(client: httpx.Client, api: str, report: Report) -> bool:
    """Liveness. Everything else is pointless if this fails."""
    print("\n=== 1. Backend health ===")

    response, elapsed, error = timed(
        lambda: client.get(f"{api}/api/v1/health", timeout=COLD_START_TIMEOUT)
    )
    if error is not None:
        report.add(
            Check(
                "GET /api/v1/health",
                "FAIL",
                elapsed,
                f"{type(error).__name__}: {error}",
            )
        )
        return False

    assert response is not None
    if response.status_code != 200:
        report.add(
            Check("GET /api/v1/health", "FAIL", elapsed, f"HTTP {response.status_code}")
        )
        return False

    body = response.json()
    report.add(
        Check(
            "GET /api/v1/health",
            "PASS",
            elapsed,
            f"v{body.get('version')} · env={body.get('environment')} "
            f"· scheduler={body.get('scheduler_enabled')}",
        )
    )

    # A production deployment still reporting environment=local means APP_ENV
    # was never set, which also leaves DEBUG logging on.
    if body.get("environment") == "local" and "onrender.com" in api:
        report.add(
            Check(
                "APP_ENV is set",
                "WARN",
                None,
                "Deployed service reports environment=local. Set APP_ENV=production.",
                required=False,
            )
        )
    return True


def check_docs(client: httpx.Client, api: str, report: Report) -> None:
    print("\n=== 2. API surface ===")

    for label, path in [("Swagger UI", "/docs"), ("OpenAPI schema", "/openapi.json")]:
        response, elapsed, error = timed(
            lambda p=path: client.get(f"{api}{p}", timeout=30)
        )
        if error is not None or response is None or response.status_code != 200:
            detail = str(error) if error else f"HTTP {response.status_code}"  # type: ignore[union-attr]
            report.add(Check(label, "FAIL", elapsed, detail))
            continue

        if path == "/openapi.json":
            paths = response.json().get("paths", {})
            report.add(Check(label, "PASS", elapsed, f"{len(paths)} endpoints"))
        else:
            report.add(Check(label, "PASS", elapsed))


def check_dependencies(client: httpx.Client, api: str, report: Report) -> None:
    """DataHub and the LLM. Both optional — the app degrades honestly."""
    print("\n=== 3. Dependencies ===")

    response, elapsed, error = timed(
        lambda: client.get(f"{api}/api/v1/health/datahub", timeout=60)
    )
    if error is not None or response is None:
        report.add(Check("DataHub connectivity", "WARN", elapsed, str(error), required=False))
    else:
        body = response.json()
        if body.get("reachable"):
            report.add(
                Check(
                    "DataHub connectivity",
                    "PASS",
                    elapsed,
                    f"GMS {body.get('version')} · {body.get('latency_ms', 0):.0f}ms",
                )
            )
        else:
            report.add(
                Check(
                    "DataHub connectivity",
                    "WARN",
                    elapsed,
                    f"Unreachable: {body.get('error')}. The UI falls back to "
                    "Demo Mode with a visible banner.",
                    required=False,
                )
            )

    response, elapsed, error = timed(
        lambda: client.get(f"{api}/api/v1/health/llm", timeout=60)
    )
    if error is not None or response is None:
        report.add(Check("LLM connectivity", "WARN", elapsed, str(error), required=False))
    else:
        body = response.json()
        if body.get("reachable"):
            report.add(
                Check(
                    "LLM connectivity",
                    "PASS",
                    elapsed,
                    f"{body.get('provider')} · {body.get('model')}",
                )
            )
        elif not body.get("configured"):
            report.add(
                Check(
                    "LLM connectivity",
                    "WARN",
                    elapsed,
                    "No API key configured. Findings and scores still work; "
                    "only the written explanation is unavailable.",
                    required=False,
                )
            )
        else:
            report.add(
                Check(
                    "LLM connectivity",
                    "WARN",
                    elapsed,
                    f"Configured but unreachable: {body.get('error')}",
                    required=False,
                )
            )


def check_data_endpoints(client: httpx.Client, api: str, report: Report) -> None:
    print("\n=== 4. Data endpoints ===")

    for label, path in [
        ("GET /datasets", "/api/v1/datasets?count=3"),
        ("GET /owners", "/api/v1/owners"),
        ("GET /domains", "/api/v1/domains?count=3"),
    ]:
        response, elapsed, error = timed(
            lambda p=path: client.get(f"{api}{p}", timeout=60)
        )
        if error is not None or response is None:
            report.add(Check(label, "WARN", elapsed, str(error), required=False))
            continue

        # 503 here means DataHub is down, which the health check already
        # reported. Not a second failure.
        if response.status_code == 503:
            report.add(
                Check(label, "WARN", elapsed, "DataHub unavailable", required=False)
            )
        elif response.status_code == 200:
            body = response.json()
            total = body.get("total") if isinstance(body, dict) else len(body)
            report.add(Check(label, "PASS", elapsed, f"{total} records"))
        else:
            report.add(
                Check(label, "FAIL", elapsed, f"HTTP {response.status_code}")
            )


def check_agent(client: httpx.Client, api: str, report: Report) -> None:
    """The product's core capability."""
    print("\n=== 5. Agent ===")

    response, elapsed, error = timed(
        lambda: client.post(
            f"{api}/api/v1/agent/analyze",
            json={"question": "Find datasets without owners"},
            timeout=AGENT_TIMEOUT,
        )
    )

    if error is not None or response is None:
        report.add(
            Check("POST /agent/analyze", "FAIL", elapsed, f"{type(error).__name__}: {error}")
        )
        return

    if response.status_code != 200:
        report.add(
            Check(
                "POST /agent/analyze",
                "FAIL",
                elapsed,
                f"HTTP {response.status_code}: {response.text[:160]}",
            )
        )
        return

    body = response.json()

    # Contract check — the UI depends on every one of these keys.
    missing = [
        key
        for key in (
            "summary",
            "risk_level",
            "risk_score",
            "findings",
            "recommendations",
            "trace",
        )
        if key not in body
    ]
    if missing:
        report.add(
            Check(
                "Agent response contract",
                "FAIL",
                elapsed,
                f"Missing keys: {', '.join(missing)}",
            )
        )
        return

    report.add(
        Check(
            "POST /agent/analyze",
            "PASS",
            elapsed,
            f"intent={body['intent']} risk={body['risk_level']}/{body['risk_score']} "
            f"findings={len(body['findings'])} degraded={body['degraded']}",
        )
    )

    # The trace is what proves the agent planned rather than ran a fixed
    # pipeline. Its absence would be a real regression.
    nodes = [entry["node"] for entry in body.get("trace", [])]
    if nodes:
        report.add(
            Check("Execution trace present", "PASS", None, " -> ".join(nodes))
        )
    else:
        report.add(Check("Execution trace present", "FAIL", None, "Trace was empty"))

    if body.get("degraded"):
        report.add(
            Check(
                "Agent ran with full evidence",
                "WARN",
                None,
                f"Degraded: {'; '.join(body.get('errors', [])[:2])}",
                required=False,
            )
        )


def check_cors(client: httpx.Client, api: str, web: str | None, report: Report) -> None:
    """The failure that only shows up in a browser."""
    print("\n=== 6. CORS ===")

    if not web:
        report.add(
            Check("CORS pre-flight", "SKIP", None, "No --web origin given", required=False)
        )
        return

    origin = web.rstrip("/")
    response, elapsed, error = timed(
        lambda: client.options(
            f"{api}/api/v1/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
            timeout=60,
        )
    )

    if error is not None or response is None:
        report.add(Check("CORS pre-flight", "FAIL", elapsed, str(error)))
        return

    allowed = response.headers.get("access-control-allow-origin")
    if allowed in (origin, "*"):
        if allowed == "*":
            report.add(
                Check(
                    "CORS pre-flight",
                    "WARN",
                    elapsed,
                    "Wildcard origin allowed. Restrict CORS_ORIGINS to the "
                    "frontend origin.",
                    required=False,
                )
            )
        else:
            report.add(Check("CORS pre-flight", "PASS", elapsed, f"allows {allowed}"))
    else:
        report.add(
            Check(
                "CORS pre-flight",
                "FAIL",
                elapsed,
                f"Origin {origin} is NOT allowed (got {allowed!r}). Every "
                f"browser request will fail. Set CORS_ORIGINS={origin}",
            )
        )


def check_frontend(client: httpx.Client, web: str | None, report: Report) -> None:
    print("\n=== 7. Frontend ===")

    if not web:
        report.add(
            Check("Frontend reachable", "SKIP", None, "No --web given", required=False)
        )
        return

    response, elapsed, error = timed(
        lambda: client.get(web, timeout=COLD_START_TIMEOUT)
    )
    if error is not None or response is None:
        report.add(Check("Frontend reachable", "FAIL", elapsed, str(error)))
        return

    if response.status_code != 200:
        report.add(
            Check("Frontend reachable", "FAIL", elapsed, f"HTTP {response.status_code}")
        )
        return

    html = response.text
    report.add(Check("Frontend reachable", "PASS", elapsed))

    if "<div id=\"root\">" in html:
        report.add(Check("SPA root present", "PASS", None))
    else:
        report.add(Check("SPA root present", "FAIL", None, "No #root element"))

    # A deep link returning 404 means the SPA rewrite rule is missing — the
    # app works until someone refreshes on a sub-route.
    deep, deep_ms, deep_err = timed(
        lambda: client.get(f"{web.rstrip('/')}/governance", timeout=60)
    )
    if deep_err is None and deep is not None and deep.status_code == 200:
        report.add(Check("SPA deep-link rewrite", "PASS", deep_ms, "/governance serves index.html"))
    else:
        status = deep.status_code if deep is not None else "error"
        report.add(
            Check(
                "SPA deep-link rewrite",
                "FAIL",
                deep_ms,
                f"/governance returned {status}. Add the rewrite rule from render.yaml.",
            )
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api", default="http://localhost:8000", help="Backend base URL"
    )
    parser.add_argument("--web", default=None, help="Frontend base URL")
    parser.add_argument("--json", default=None, help="Write the report to this path")
    parser.add_argument(
        "--skip-agent",
        action="store_true",
        help="Skip the agent check (it costs tokens and takes time)",
    )
    args = parser.parse_args()

    api = args.api.rstrip("/")
    web = args.web.rstrip("/") if args.web else None

    print("=" * 72)
    print("DataGuardian AI — deployment smoke test")
    print("=" * 72)
    print(f"  API : {api}")
    print(f"  Web : {web or '(not checked)'}")
    if "onrender.com" in api:
        print("  Note: Render free tier cold-starts can take ~50s on first request.")

    report = Report(api_url=api, web_url=web)

    with httpx.Client(follow_redirects=True) as client:
        alive = check_health(client, api, report)

        if not alive:
            print("\n" + "=" * 72)
            print("BLOCKED — the backend did not respond, so nothing else was checked.")
            print("  · Is the service awake? Free-tier services sleep when idle.")
            print("  · Check the Render logs for a start-command failure.")
            print("  · Confirm the start command binds $PORT and host 0.0.0.0.")
            print("=" * 72)
            return 1

        check_docs(client, api, report)
        check_dependencies(client, api, report)
        check_data_endpoints(client, api, report)
        if not args.skip_agent:
            check_agent(client, api, report)
        check_cors(client, api, web, report)
        check_frontend(client, web, report)

    # --- Summary --------------------------------------------------------------
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)

    passed = sum(1 for c in report.checks if c.status == "PASS")
    print(
        f"  {passed} passed · {len(report.failures)} failed · "
        f"{len(report.warnings)} warnings"
    )

    latencies = [c.latency_ms for c in report.checks if c.latency_ms is not None]
    if latencies:
        print(
            f"  latency: avg={sum(latencies) / len(latencies):.0f}ms  "
            f"max={max(latencies):.0f}ms"
        )

    if report.warnings:
        print("\n  WARNINGS (deployment still usable):")
        for check in report.warnings:
            print(f"    · {check.name}: {check.detail}")

    if report.failures:
        print("\n  FAILURES (must fix):")
        for check in report.failures:
            print(f"    · {check.name}: {check.detail}")

    print("\n  " + ("DEPLOYMENT OK" if report.ok else "DEPLOYMENT BROKEN"))
    print("=" * 72)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "api_url": report.api_url,
                    "web_url": report.web_url,
                    "ok": report.ok,
                    "checks": [asdict(c) for c in report.checks],
                },
                handle,
                indent=2,
            )
        print(f"\n  Report written to {args.json}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
