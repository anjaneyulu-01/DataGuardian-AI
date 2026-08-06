"""Gemini provider, via Google's OpenAI-compatible endpoint.

Google exposes `/v1beta/openai/chat/completions` alongside its native
`generateContent` API. Using the compatible surface means Gemini reuses the
shared transport in `openai_compatible.py` instead of needing a bespoke
implementation — configuration only, same as Groq and Grok.

Model note: Gemini 2.5 models are *thinking* models. They spend part of the
token budget on internal reasoning before emitting visible text, so a small
`LLM_MAX_TOKENS` can return `finish_reason="length"` with empty content. The
shared transport detects exactly that case and raises an actionable error
rather than a bare "empty completion". The 4096 default leaves ample room.
"""

import httpx

from app.config import Settings
from app.config import settings as default_settings
from app.llm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderConfig,
)


class GeminiProvider(OpenAICompatibleProvider):
    """Google Gemini, over its OpenAI-compatible chat-completions surface."""

    name = "gemini"

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        resolved = settings or default_settings
        super().__init__(
            config=ProviderConfig(
                vendor="Gemini",
                key_env_var="GEMINI_API_KEY",
                console_url="https://aistudio.google.com/apikey",
                api_key=resolved.gemini_api_key,
                base_url=resolved.gemini_base_url,
                model=resolved.llm_model or resolved.gemini_model,
            ),
            settings=resolved,
            transport=transport,
        )
