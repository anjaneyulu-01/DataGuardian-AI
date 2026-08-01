"""In-memory TTL cache for DataHub reads.

DataHub metadata changes on an ingestion cadence — minutes to hours — not per
request. Re-querying GMS for the same dataset list on every call wastes the
most expensive resource in the stack. A short TTL absorbs that without ever
serving genuinely stale governance data.

Two properties matter and are both tested:

* **Failures are never cached.** If the factory raises, nothing is stored, so
  a DataHub outage cannot pin an error in place for the whole TTL. The next
  caller retries for real.
* **Single-flight.** Concurrent misses for the same key wait on one in-flight
  call rather than stampeding GMS. This is the difference between a cache
  that protects the upstream and one that only helps when it is already warm.

Scope: one process. That is the right size for this project — the API and the
scheduler run in the same process, and a shared cache (Redis) would add an
operational dependency for no benefit at this stage.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CacheStats:
    """Counters for observability. Exposed on the health endpoint."""

    hits: int
    misses: int
    entries: int
    evictions: int

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


@dataclass
class _Entry:
    value: Any
    expires_at: float


class TTLCache:
    """Async-safe, size-bounded TTL cache with single-flight loading."""

    def __init__(self, ttl_seconds: float = 60.0, max_entries: int = 512) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        # OrderedDict gives LRU eviction: move_to_end on read, popitem(last=False)
        # to drop the coldest entry when full.
        self._entries: OrderedDict[str, _Entry] = OrderedDict()
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    # -- Public API -----------------------------------------------------------

    async def get_or_load[T](self, key: str, factory: Callable[[], Awaitable[T]]) -> T:
        """Return the cached value for `key`, or load and store it.

        `factory` is awaited only on a miss. If it raises, the exception
        propagates and nothing is cached.
        """
        cached = self._read(key)
        if cached is not _MISS:
            self._hits += 1
            logger.debug("DataHub cache hit: %s", key)
            return cached

        # Serialise concurrent misses for the same key so only one request
        # reaches DataHub.
        lock = await self._lock_for(key)
        async with lock:
            # Another waiter may have populated the entry while we queued.
            cached = self._read(key)
            if cached is not _MISS:
                self._hits += 1
                return cached

            self._misses += 1
            logger.debug("DataHub cache miss: %s", key)

            # Deliberately not wrapped in try/except: an exception must
            # propagate without writing an entry.
            value = await factory()
            self._write(key, value)
            return value

    def invalidate(self, key: str) -> None:
        """Drop one entry. Used after a write-back to DataHub."""
        self._entries.pop(key, None)

    def clear(self) -> None:
        """Drop everything."""
        self._entries.clear()

    def stats(self) -> CacheStats:
        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            entries=len(self._entries),
            evictions=self._evictions,
        )

    # -- Internals ------------------------------------------------------------

    def _read(self, key: str) -> Any:
        entry = self._entries.get(key)
        if entry is None:
            return _MISS
        if entry.expires_at <= time.monotonic():
            # Expired entries are removed lazily, on access. A sweeper task
            # would cost a background thread for no real benefit at this size.
            self._entries.pop(key, None)
            return _MISS
        self._entries.move_to_end(key)
        return entry.value

    def _write(self, key: str, value: Any) -> None:
        self._entries[key] = _Entry(
            value=value, expires_at=time.monotonic() + self._ttl
        )
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)
            self._evictions += 1

    async def _lock_for(self, key: str) -> asyncio.Lock:
        """Get (or create) the per-key single-flight lock."""
        async with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            # Prevent unbounded growth of the lock table on a long-running
            # process with high key cardinality.
            if len(self._locks) > self._max_entries * 2:
                for stale in [k for k in self._locks if k not in self._entries][:100]:
                    if not self._locks[stale].locked():
                        del self._locks[stale]
            return lock


class NullCache(TTLCache):
    """A cache that never stores anything.

    Injected when caching is disabled, so `service.py` has no `if self._cache`
    branches and the cached and uncached paths cannot diverge.
    """

    def __init__(self) -> None:
        super().__init__(ttl_seconds=0.0, max_entries=0)

    async def get_or_load[T](self, key: str, factory: Callable[[], Awaitable[T]]) -> T:
        return await factory()


def build_cache_key(operation: str, **params: object) -> str:
    """Build a stable cache key from an operation name and its parameters.

    Parameters are sorted so argument order cannot produce two keys for the
    same logical call.
    """
    if not params:
        return operation
    rendered = ",".join(f"{k}={v!r}" for k, v in sorted(params.items()))
    return f"{operation}({rendered})"


# Sentinel distinguishing "cached value is None" from "not cached".
_MISS: Any = object()
