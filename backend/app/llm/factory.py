"""Provider selection.

`LLM_PROVIDER` in the environment decides which `BaseLLM` implementation the
application runs. Business logic never imports a concrete provider — it asks
the factory (or receives the instance via DI) and programs against `BaseLLM`.

Adding a provider is three steps, none of which touch business logic:

1. Implement `chat()` and `health()` in `providers/<name>.py`.
2. Register the constructor in `_REGISTRY` below.
3. Add its credentials to `Settings` and `.env.example`.
"""

import logging
from collections.abc import Callable

from app.config import Settings
from app.config import settings as default_settings
from app.llm.base import BaseLLM
from app.llm.exceptions import LLMProviderNotSupportedError
from app.llm.providers.grok import GrokProvider

logger = logging.getLogger(__name__)


def _not_implemented(name: str) -> Callable[[Settings], BaseLLM]:
    """Registered-but-unbuilt provider: fail with a clear, honest message."""

    def raiser(_settings: Settings) -> BaseLLM:
        raise LLMProviderNotSupportedError(
            f"LLM provider '{name}' is planned but not implemented yet. "
            "Set LLM_PROVIDER=grok, or implement "
            f"app/llm/providers/{name}.py and register it in factory.py"
        )

    return raiser


# The full roster the product intends to support. Placeholders raise a
# precise error instead of the generic "unknown provider".
_REGISTRY: dict[str, Callable[[Settings], BaseLLM]] = {
    "grok": lambda settings: GrokProvider(settings=settings),
    "gemini": _not_implemented("gemini"),
    "openai": _not_implemented("openai"),
    "claude": _not_implemented("claude"),
}


class LLMFactory:
    """Builds the configured LLM provider."""

    @staticmethod
    def create(settings: Settings | None = None) -> BaseLLM:
        """Return the provider named by ``LLM_PROVIDER``.

        Raises:
            LLMProviderNotSupportedError: Unknown name, or a registered
                placeholder that has no implementation yet.
        """
        resolved = settings or default_settings
        provider_name = resolved.llm_provider.strip().lower()

        builder = _REGISTRY.get(provider_name)
        if builder is None:
            supported = ", ".join(sorted(_REGISTRY))
            raise LLMProviderNotSupportedError(
                f"Unknown LLM provider '{provider_name}'. Supported values: {supported}"
            )

        provider = builder(resolved)
        logger.info("LLM provider ready: %s", provider.name)
        return provider

    @staticmethod
    def supported_providers() -> list[str]:
        """Every registered provider name, implemented or planned."""
        return sorted(_REGISTRY)
