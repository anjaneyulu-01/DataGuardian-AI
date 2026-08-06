"""OpenAI provider.

The reference implementation of the protocol every other provider in this
package imitates, so it is configuration only.

Module name note: this file is `app.llm.providers.openai`, which would shadow
the third-party `openai` package for anything doing a bare `import openai`
inside this directory. Nothing here does — the shared transport uses httpx —
and absolute imports elsewhere in the app resolve to the installed package as
normal.
"""

import httpx

from app.config import Settings
from app.config import settings as default_settings
from app.llm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderConfig,
)


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI models over the chat-completions API."""

    name = "openai"

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        resolved = settings or default_settings
        super().__init__(
            config=ProviderConfig(
                vendor="OpenAI",
                key_env_var="OPENAI_API_KEY",
                console_url="https://platform.openai.com/api-keys",
                api_key=resolved.openai_api_key,
                base_url=resolved.openai_base_url,
                model=resolved.llm_model or resolved.openai_model,
            ),
            settings=resolved,
            transport=transport,
        )
