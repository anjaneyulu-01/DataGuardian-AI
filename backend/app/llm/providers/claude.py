"""Claude provider, via Anthropic's OpenAI-compatible layer.

Anthropic's native API is `/v1/messages`, which uses a different request and
response shape. It also publishes an OpenAI compatibility layer exposing
`/v1/chat/completions`, and using that keeps Claude on the shared transport —
configuration only, like every other provider here.

TODO(llm): The compatibility layer is a convenience surface and does not
expose everything the native Messages API does (extended thinking controls,
fine-grained tool-use blocks, prompt caching). If the agent later needs those,
reimplement this class against `BaseLLM` directly and talk to `/v1/messages`.
Nothing outside this file changes when that happens — no caller imports
`ClaudeProvider`.
"""

import httpx

from app.config import Settings
from app.config import settings as default_settings
from app.llm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderConfig,
)


class ClaudeProvider(OpenAICompatibleProvider):
    """Anthropic Claude, over the OpenAI-compatible chat-completions surface."""

    name = "claude"

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        resolved = settings or default_settings
        super().__init__(
            config=ProviderConfig(
                vendor="Anthropic",
                key_env_var="ANTHROPIC_API_KEY",
                console_url="https://console.anthropic.com/settings/keys",
                api_key=resolved.anthropic_api_key,
                base_url=resolved.anthropic_base_url,
                model=resolved.llm_model or resolved.anthropic_model,
            ),
            settings=resolved,
            transport=transport,
        )
