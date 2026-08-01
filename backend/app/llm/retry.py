"""Retry policy for transient LLM-provider failures.

Deliberately parallel to ``app.integrations.datahub.retry`` rather than shared
with it: the two layers classify different exception families, and coupling
them would make a DataHub tweak silently change LLM behaviour. The ~40 lines
of similarity are the cost of that independence.

Retryable: connection failures, timeouts, rate limits (the provider told us
to come back). Not retryable: bad credentials, unsupported provider, invalid
response — those fail identically every time.
"""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from app.llm.exceptions import (
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)

_RETRYABLE = (LLMConnectionError, LLMTimeoutError, LLMRateLimitError)

# Provider HTTP statuses that mean "try again shortly".
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, _RETRYABLE)


async def with_retry[T](
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    base_delay: float = 1.0,
    max_delay: float = 20.0,
    description: str = "LLM request",
) -> T:
    """Run `operation`, retrying transient failures with full-jitter backoff.

    Rate limits get a longer base wait than the DataHub retry helper uses —
    LLM 429s typically clear in seconds, not milliseconds, and hammering the
    endpoint extends the penalty window.
    """
    total = max(1, attempts)

    for attempt in range(1, total + 1):
        try:
            return await operation()
        except LLMError as exc:
            if not is_retryable(exc) or attempt == total:
                if is_retryable(exc):
                    logger.warning(
                        "%s failed after %d attempt(s): %s",
                        description,
                        total,
                        exc.detail,
                    )
                raise

            # Rate limits back off harder than plain connection blips.
            base = base_delay * 3 if isinstance(exc, LLMRateLimitError) else base_delay
            capped = min(max_delay, base * (2 ** (attempt - 1)))
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

    raise RuntimeError("unreachable")  # loop always returns or raises
