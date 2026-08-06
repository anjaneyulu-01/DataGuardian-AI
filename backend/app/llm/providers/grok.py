"""Grok provider, via xAI's OpenAI-compatible REST API.

All transport, retry, and mapping logic lives in `OpenAICompatibleProvider`.
This file supplies only what is specific to xAI, which is why it is short.

Implementation choice: plain ``httpx`` against ``/chat/completions`` rather
than a vendor SDK. xAI documents the OpenAI-compatible endpoint as a
first-class interface, httpx is already a project dependency with an
established mock-transport testing pattern, and skipping the SDK keeps the
dependency tree flat. If ``xai-sdk`` later becomes compelling (server-side
tools, native streaming helpers), it slots in behind this same class without
touching any caller.

NOTE: xAI ("Grok") is unrelated to Groq (`providers/groq.py`) despite the
near-identical name. Keys are not interchangeable — xAI keys start `xai-`,
Groq keys start `gsk_`.
"""

import httpx

from app.config import Settings
from app.config import settings as default_settings
from app.llm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderConfig,
)


class GrokProvider(OpenAICompatibleProvider):
    """xAI Grok, over the OpenAI-compatible chat-completions API."""

    name = "grok"

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        resolved = settings or default_settings
        super().__init__(
            config=ProviderConfig(
                vendor="xAI",
                key_env_var="XAI_API_KEY",
                console_url="https://console.x.ai",
                api_key=resolved.xai_api_key,
                base_url=resolved.xai_base_url,
                model=resolved.llm_model or resolved.xai_model,
            ),
            settings=resolved,
            transport=transport,
        )
