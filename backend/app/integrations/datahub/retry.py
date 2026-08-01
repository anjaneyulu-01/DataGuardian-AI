"""Retry policy for transient DataHub failures.

Only *transient* failures are retried: the connection never landed, or GMS
answered with a status that means "try again later". A rejected token, a
GraphQL schema mismatch, or a missing entity will fail identically on every
attempt, so retrying them just multiplies latency and log noise.

Backoff is exponential with full jitter. Without jitter, several workers that
fail together retry together, and the retries themselves become the load
spike that keeps GMS down.

SAFETY: every operation this integration performs is a read. Replaying a read
is harmless. If a write (a remediation mutation) is added later, it must
either be idempotent or bypass this helper — see `is_retryable`.
"""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from app.integrations.datahub.exceptions import (
    DataHubConnectionError,
    DataHubError,
    DataHubTimeoutError,
)

logger = logging.getLogger(__name__)

# Transport-level failures worth another attempt.
_RETRYABLE_EXCEPTIONS = (DataHubConnectionError, DataHubTimeoutError)

# GMS status codes that indicate a temporary condition. 502/503/504 appear
# while DataHub is still booting, which is exactly when a retry helps.
RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})


def is_retryable(exc: BaseException) -> bool:
    """Whether another attempt could plausibly succeed.

    Authentication errors, query errors, and not-found are deliberately
    excluded — they are deterministic.
    """
    return isinstance(exc, _RETRYABLE_EXCEPTIONS)


async def with_retry[T](
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    base_delay: float,
    max_delay: float,
    description: str = "DataHub request",
) -> T:
    """Run `operation`, retrying transient failures with jittered backoff.

    Args:
        operation: Zero-argument coroutine factory. Called once per attempt,
            so it must be re-callable rather than an already-awaited coroutine.
        attempts: Total attempts including the first. `1` disables retrying.
        base_delay: Seconds before the first retry; doubles each time.
        max_delay: Ceiling for a single sleep.
        description: Used in log messages to identify the operation.

    Returns:
        Whatever `operation` returns.

    Raises:
        The last exception, once attempts are exhausted or the failure is not
        retryable. The original error type is preserved so callers still see
        `DataHubTimeoutError` rather than a wrapper.
    """
    total = max(1, attempts)
    last_error: BaseException | None = None

    for attempt in range(1, total + 1):
        try:
            return await operation()
        except DataHubError as exc:
            last_error = exc

            if not is_retryable(exc):
                raise

            if attempt == total:
                logger.warning(
                    "%s failed after %d attempt(s): %s",
                    description,
                    total,
                    exc.detail,
                )
                raise

            # Full jitter: sleep anywhere in [0, capped_backoff]. Spreads
            # retries out instead of synchronising them.
            capped = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay = random.uniform(0, capped)
            logger.info(
                "%s failed (attempt %d/%d): %s. Retrying in %.2fs",
                description,
                attempt,
                total,
                exc.detail,
                delay,
            )
            await asyncio.sleep(delay)

    # Unreachable: the loop either returns or raises. Present so the function
    # is total for type checkers.
    raise last_error if last_error else RuntimeError("retry loop exited")
