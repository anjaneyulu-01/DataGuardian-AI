"""Groq provider, via Groq's OpenAI-compatible REST API.

Groq is an inference host serving open-weight models (Llama, Mixtral, Qwen)
on custom silicon. It is a different company from xAI, whose model is called
"Grok" — the names are nearly identical and the keys are NOT interchangeable:

    xAI  (Grok)   keys start `xai-`   https://console.x.ai
    Groq          keys start `gsk_`   https://console.groq.com

Because Groq exposes the same OpenAI-compatible protocol as xAI, this file
supplies configuration only; every byte of transport, retry, and mapping
logic is inherited from `OpenAICompatibleProvider`.

Model note: `llama-3.3-70b-versatile` is the default because it balances
quality against Groq's very high throughput, and it supports the JSON
response format that `structured_output()` relies on. Override with
GROQ_MODEL.
"""

import httpx

from app.config import Settings
from app.config import settings as default_settings
from app.llm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderConfig,
)


class GroqProvider(OpenAICompatibleProvider):
    """Groq-hosted open-weight models, over the chat-completions API."""

    name = "groq"

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        resolved = settings or default_settings
        super().__init__(
            config=ProviderConfig(
                vendor="Groq",
                key_env_var="GROQ_API_KEY",
                console_url="https://console.groq.com/keys",
                api_key=resolved.groq_api_key,
                base_url=resolved.groq_base_url,
                model=resolved.llm_model or resolved.groq_model,
            ),
            settings=resolved,
            transport=transport,
        )
