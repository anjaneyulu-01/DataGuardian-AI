"""Node instrumentation and failure containment.

Every node in the graph is wrapped by `run_node`, which supplies four things
that would otherwise be copy-pasted nine times:

* **Timing** — wall-clock duration per node, for the trace and the UI.
* **Structured logging** — one line per node, at a consistent level.
* **Failure containment** — a tool raising does not kill the run. The node is
  marked FAILED, the error is recorded, `degraded` is set, and the graph
  continues with whatever evidence it has.
* **Trace accumulation** — an ordered record of what actually executed, which
  is how a multi-step agent stays debuggable.

Containment is the important one. A governance answer built from partial
metadata is genuinely useful — "DataHub returned owners but lineage timed out"
still tells a steward something. An exception page tells them nothing. The
`degraded` flag ensures partial answers are never mistaken for complete ones.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.agents.state import AgentState, NodeStatus, TraceEntry

logger = logging.getLogger(__name__)

#: A node: takes state, returns the keys it changed.
NodeFn = Callable[[AgentState], Awaitable[dict[str, Any]]]

# Duration above which a node is logged as slow.
SLOW_NODE_MS = 2000.0


async def run_node(
    name: str,
    state: AgentState,
    fn: NodeFn,
    *,
    detail: str = "",
) -> dict[str, Any]:
    """Execute one node with timing, logging, and failure containment.

    Args:
        name: Node name as it appears in the trace.
        state: Current graph state.
        fn: The node body.
        detail: Optional note recorded in the trace (e.g. which tool ran).

    Returns:
        The node's state update, always including a `trace` entry. On failure,
        returns only the trace, the error, and `degraded=True` — never a
        partial or invented result.
    """
    started = time.perf_counter()

    try:
        update = await fn(state)
        duration_ms = (time.perf_counter() - started) * 1000

        log = logger.warning if duration_ms > SLOW_NODE_MS else logger.info
        log(
            "agent.node ok    %-16s %7.0fms %s",
            name,
            duration_ms,
            detail or _summarise(update),
        )

        return {
            **update,
            "trace": [
                TraceEntry(
                    node=name,
                    status=NodeStatus.OK,
                    duration_ms=duration_ms,
                    detail=detail or _summarise(update),
                )
            ],
        }

    except Exception as exc:
        duration_ms = (time.perf_counter() - started) * 1000
        message = _describe(exc)

        logger.exception(
            "agent.node FAIL  %-16s %7.0fms %s", name, duration_ms, message
        )

        return {
            "trace": [
                TraceEntry(
                    node=name,
                    status=NodeStatus.FAILED,
                    duration_ms=duration_ms,
                    detail=detail,
                    error=message,
                )
            ],
            "errors": [f"{name}: {message}"],
            "degraded": True,
        }


def skipped(name: str, reason: str) -> dict[str, Any]:
    """Trace entry for a node the planner chose not to run.

    Recorded rather than silently omitted: "why didn't it check lineage?" is a
    question the trace should answer.
    """
    logger.debug("agent.node skip  %-16s %s", name, reason)
    return {
        "trace": [
            TraceEntry(
                node=name,
                status=NodeStatus.SKIPPED,
                duration_ms=0.0,
                detail=reason,
            )
        ]
    }


def _describe(exc: Exception) -> str:
    """Human-readable error, preferring our typed `detail` when present."""
    detail = getattr(exc, "detail", None)
    if isinstance(detail, str) and detail:
        return f"{type(exc).__name__}: {detail}"
    return f"{type(exc).__name__}: {exc}"


def _summarise(update: dict[str, Any]) -> str:
    """One-line description of what a node produced, for logs and the trace."""
    parts: list[str] = []
    for key, value in update.items():
        if key in ("trace", "errors"):
            continue
        if isinstance(value, list):
            parts.append(f"{key}={len(value)}")
        elif isinstance(value, dict):
            parts.append(f"{key}={{{len(value)}}}")
        elif isinstance(value, str):
            parts.append(f"{key}={value[:40]!r}" if value else f"{key}=''")
        else:
            parts.append(f"{key}={value}")
    return " ".join(parts) or "no changes"
