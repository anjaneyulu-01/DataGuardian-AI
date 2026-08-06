"""Provider selection.

`LLM_PROVIDER` decides which `BaseLLM` implementation the application runs.
Business logic never imports a concrete provider — it asks the factory (or
receives the instance via DI) and programs against `BaseLLM`.

Three ways to configure it, all env-only:

    LLM_PROVIDER=auto     first provider in LLM_PROVIDER_ORDER that has a key
    LLM_PROVIDER=groq     pin to one provider; fail loudly if it has no key
    LLM_MODEL=<name>      override the active provider's model

With `LLM_FALLBACK_ENABLED` (default true) and more than one key configured,
the result is a `FallbackProvider`: transient failures on the primary roll
over to the next configured provider automatically. Deterministic failures
never roll over — see `providers/fallback.py`.

Adding a provider is three steps, none of which touch business logic:

1. Implement it in `providers/<name>.py` (usually a `ProviderConfig` subclass).
2. Register it in `_REGISTRY` below.
3. Add its credentials to `Settings` and the root `.env.example`.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from app.config import Settings
from app.config import settings as default_settings
from app.llm.base import BaseLLM
from app.llm.exceptions import LLMConfigurationError, LLMProviderNotSupportedError
from app.llm.providers.claude import ClaudeProvider
from app.llm.providers.fallback import FallbackProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.grok import GrokProvider
from app.llm.providers.groq import GroqProvider
from app.llm.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)

#: Sentinel for "choose for me".
AUTO = "auto"


@dataclass(frozen=True)
class ProviderSpec:
    """How to build a provider, and how to tell whether it is usable."""

    build: Callable[[Settings], BaseLLM]
    #: Reads the provider's API key off Settings. `None`/empty = unconfigured.
    api_key: Callable[[Settings], str | None]
    #: The variable a user sets to enable it, named in error messages.
    key_env_var: str


_REGISTRY: dict[str, ProviderSpec] = {
    # NOTE: `grok` (xAI) and `groq` (Groq Inc) are different vendors despite
    # the one-letter difference. See the note in each provider module.
    "groq": ProviderSpec(
        build=lambda s: GroqProvider(settings=s),
        api_key=lambda s: s.groq_api_key,
        key_env_var="GROQ_API_KEY",
    ),
    "grok": ProviderSpec(
        build=lambda s: GrokProvider(settings=s),
        api_key=lambda s: s.xai_api_key,
        key_env_var="XAI_API_KEY",
    ),
    "gemini": ProviderSpec(
        build=lambda s: GeminiProvider(settings=s),
        api_key=lambda s: s.gemini_api_key,
        key_env_var="GEMINI_API_KEY",
    ),
    "openai": ProviderSpec(
        build=lambda s: OpenAIProvider(settings=s),
        api_key=lambda s: s.openai_api_key,
        key_env_var="OPENAI_API_KEY",
    ),
    "claude": ProviderSpec(
        build=lambda s: ClaudeProvider(settings=s),
        api_key=lambda s: s.anthropic_api_key,
        key_env_var="ANTHROPIC_API_KEY",
    ),
}


class LLMFactory:
    """Builds the configured LLM provider."""

    @staticmethod
    def create(settings: Settings | None = None) -> BaseLLM:
        """Return the provider (or fail-over chain) the config asks for.

        Raises:
            LLMProviderNotSupportedError: `LLM_PROVIDER` names something that
                is not registered.
            LLMConfigurationError: `LLM_PROVIDER=auto` but no provider has a
                key, so there is nothing to select.
        """
        resolved = settings or default_settings
        requested = resolved.llm_provider.strip().lower()

        if requested == AUTO:
            provider = LLMFactory._create_auto(resolved)
        else:
            spec = _REGISTRY.get(requested)
            if spec is None:
                supported = ", ".join(sorted(_REGISTRY))
                raise LLMProviderNotSupportedError(
                    f"Unknown LLM provider '{requested}'. "
                    f"Supported: {supported}, or 'auto'."
                )
            provider = LLMFactory._maybe_wrap(spec.build(resolved), requested, resolved)

        logger.info(
            "LLM ready: provider=%s model=%s%s",
            provider.name,
            getattr(provider, "model", "unknown"),
            f" chain={provider.chain}"
            if isinstance(provider, FallbackProvider)
            else "",
        )
        return provider

    # -- Selection ------------------------------------------------------------------

    @staticmethod
    def _create_auto(settings: Settings) -> BaseLLM:
        """Pick the first configured provider in preference order."""
        available = LLMFactory.available_providers(settings)
        if not available:
            hint = ", ".join(
                _REGISTRY[name].key_env_var for name in LLMFactory._order(settings)
            )
            raise LLMConfigurationError(
                "LLM_PROVIDER=auto but no provider has an API key. Set one of: "
                f"{hint} in the .env at the repository root."
            )

        primary = available[0]
        logger.info(
            "LLM auto-selected '%s' (configured: %s)", primary, ", ".join(available)
        )
        return LLMFactory._maybe_wrap(
            _REGISTRY[primary].build(settings), primary, settings
        )

    @staticmethod
    def _maybe_wrap(primary: BaseLLM, primary_name: str, settings: Settings) -> BaseLLM:
        """Wrap in a fail-over chain when other providers are also configured."""
        if not settings.llm_fallback_enabled:
            return primary

        others = [
            name
            for name in LLMFactory.available_providers(settings)
            if name != primary_name
        ]
        if not others:
            return primary

        chain = [primary] + [_REGISTRY[name].build(settings) for name in others]
        return FallbackProvider(chain)

    # -- Introspection ----------------------------------------------------------------

    @staticmethod
    def available_providers(settings: Settings | None = None) -> list[str]:
        """Registered providers that have a non-empty API key, in preference order.

        "Available" means credentials exist — not that the vendor is reachable.
        Liveness is `health()`, which costs a network round-trip.
        """
        resolved = settings or default_settings
        return [
            name
            for name in LLMFactory._order(resolved)
            if (_REGISTRY[name].api_key(resolved) or "").strip()
        ]

    @staticmethod
    def supported_providers() -> list[str]:
        """Every registered provider name."""
        return sorted(_REGISTRY)

    @staticmethod
    def describe(settings: Settings | None = None) -> dict[str, object]:
        """Full configuration picture, for `/health/llm` and for debugging.

        Answers "what would run, what could run, and what is missing" without
        making a single network call.
        """
        resolved = settings or default_settings
        available = LLMFactory.available_providers(resolved)
        return {
            "requested": resolved.llm_provider,
            "active": available[0]
            if resolved.llm_provider == AUTO and available
            else (resolved.llm_provider if resolved.llm_provider != AUTO else None),
            "available": available,
            "supported": LLMFactory.supported_providers(),
            "fallback_enabled": resolved.llm_fallback_enabled,
            "fallback_chain": available[1:] if resolved.llm_fallback_enabled else [],
            "model_override": resolved.llm_model,
            "missing_keys": {
                name: _REGISTRY[name].key_env_var
                for name in LLMFactory._order(resolved)
                if name not in available
            },
        }

    @staticmethod
    def _order(settings: Settings) -> list[str]:
        """Preference order, filtered to registered names.

        Unknown entries in `LLM_PROVIDER_ORDER` are skipped with a warning
        rather than raising: a typo in the ordering should not stop the
        application from starting when other providers are usable.
        """
        order: list[str] = []
        for raw in settings.llm_provider_order:
            name = raw.strip().lower()
            if name in _REGISTRY:
                if name not in order:
                    order.append(name)
            elif name:
                logger.warning(
                    "Ignoring unknown provider '%s' in LLM_PROVIDER_ORDER", name
                )
        # Anything registered but unlisted still ranks, just last.
        order.extend(name for name in sorted(_REGISTRY) if name not in order)
        return order
