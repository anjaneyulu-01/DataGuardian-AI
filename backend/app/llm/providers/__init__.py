"""Concrete LLM providers.

One module per vendor. Nothing outside this package may import these
directly — consumers go through `LLMFactory` and program against `BaseLLM`.

`OpenAICompatibleProvider` holds the shared implementation for every vendor
speaking OpenAI's chat-completions protocol; all five providers below are
configuration-only subclasses of it. `FallbackProvider` is not a vendor — it
composes several providers into one fail-over chain.
"""

from app.llm.providers.claude import ClaudeProvider
from app.llm.providers.fallback import FallbackProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.grok import GrokProvider
from app.llm.providers.groq import GroqProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderConfig,
)

__all__ = [
    "ClaudeProvider",
    "FallbackProvider",
    "GeminiProvider",
    "GrokProvider",
    "GroqProvider",
    "OpenAICompatibleProvider",
    "OpenAIProvider",
    "ProviderConfig",
]
