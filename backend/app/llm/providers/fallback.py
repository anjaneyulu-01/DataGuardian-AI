"""Fail-over across several configured providers.

Wraps an ordered list of providers and presents the `BaseLLM` interface, so
nothing upstream knows whether it is talking to one provider or five.

The rule that makes this safe: **only transient failures fail over.**

* Rate limited, timed out, provider down  → try the next provider. The next
  one is a different vendor with a different quota, so it plausibly succeeds.
* Bad key, unknown model, malformed response → raise immediately. The next
  provider would fail the same way (or worse, silently succeed and hide a
  real misconfiguration), and the operator needs the true error.

That distinction already exists as `is_retryable` in `retry.py`; this module
reuses it rather than defining a second, drifting notion of "transient".

Ordering is `LLM_PROVIDER_ORDER`. Providers with no API key are dropped at
construction, never at call time — an unconfigured provider is not a runtime
failure, it simply is not in the chain.
"""

import logging

from app.llm.base import BaseLLM
from app.llm.exceptions import LLMConfigurationError, LLMError
from app.llm.models import ChatMessage, LLMHealth, LLMResponse
from app.llm.retry import is_retryable

logger = logging.getLogger(__name__)


class FallbackProvider(BaseLLM):
    """Tries each provider in order until one answers."""

    name = "fallback"

    def __init__(self, providers: list[BaseLLM]) -> None:
        """Build the chain.

        Args:
            providers: Ordered, non-empty list. Index 0 is primary.

        Raises:
            LLMConfigurationError: The list is empty.
        """
        if not providers:
            raise LLMConfigurationError(
                "FallbackProvider needs at least one provider. No LLM provider "
                "has an API key configured — set one in the .env at the "
                "repository root."
            )
        self._providers = providers
        self._last_successful: str | None = None

    @property
    def primary(self) -> BaseLLM:
        """The provider tried first — what `/health` reports as active."""
        return self._providers[0]

    @property
    def model(self) -> str:
        """The primary's model, so `provider.model` stays meaningful."""
        return getattr(self.primary, "model", "unknown")

    @property
    def chain(self) -> list[str]:
        """Provider names in fail-over order."""
        return [p.name for p in self._providers]

    @property
    def active_provider(self) -> str:
        """Which provider actually served the most recent call.

        Reporting "fallback" in a trace is useless when debugging — the
        question is always *which model wrote this*. Before any call has
        succeeded this is the primary, which is what would be tried next.
        """
        return self._last_successful or self.primary.name

    # -- BaseLLM ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        last_transient: LLMError | None = None

        for index, provider in enumerate(self._providers):
            try:
                response = await provider.chat(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
                self._last_successful = provider.name
                if index > 0:
                    logger.warning(
                        "LLM fail-over succeeded on '%s' (attempt %d of %d)",
                        provider.name,
                        index + 1,
                        len(self._providers),
                    )
                return response

            except LLMError as exc:
                if not is_retryable(exc):
                    # Deterministic: every provider would fail the same way, and
                    # masking it behind a fail-over hides a real misconfiguration.
                    logger.error(
                        "LLM provider '%s' failed non-transiently: %s",
                        provider.name,
                        exc.detail,
                    )
                    raise

                last_transient = exc
                remaining = len(self._providers) - index - 1
                logger.warning(
                    "LLM provider '%s' unavailable (%s): %s. %s",
                    provider.name,
                    type(exc).__name__,
                    exc.detail,
                    f"Falling back to '{self._providers[index + 1].name}'"
                    if remaining
                    else "No providers left.",
                )

        # Every provider failed transiently. Re-raise the last one so the
        # caller still sees a typed, retryable error.
        assert last_transient is not None
        raise last_transient

    async def health(self) -> LLMHealth:
        """Health of the primary, annotated with the rest of the chain.

        Reports the primary rather than probing every provider: a health check
        should be cheap, and the chain composition is static configuration
        that `LLMFactory.describe()` already exposes in full.
        """
        health = await self.primary.health()
        if len(self._providers) > 1:
            fallbacks = ", ".join(self.chain[1:])
            detail = f"fallback chain: {fallbacks}"
            health = health.model_copy(
                update={
                    "error": f"{health.error} ({detail})" if health.error else None,
                    "fallback_chain": self.chain[1:],
                }
            )
        return health

    async def aclose(self) -> None:
        """Release every provider in the chain."""
        for provider in self._providers:
            await provider.aclose()
