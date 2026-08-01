"""Grok provider, via xAI's OpenAI-compatible REST API.

Implementation choice: plain ``httpx`` against ``/chat/completions`` rather
than a vendor SDK. xAI documents the OpenAI-compatible endpoint as a
first-class interface, httpx is already a project dependency with an
established mock-transport testing pattern, and skipping the SDK keeps the
dependency tree flat. If the ``xai-sdk`` package becomes compelling
(server-side tools, native streaming helpers), it slots in behind this same
class without touching any caller.

Streaming: the transport and method signatures are structured so a
``stream=True`` path can be added to ``_post_chat`` (SSE via
``client.stream``) without changing the public interface. Deliberately not
implemented until something consumes it — see README.
"""

import logging
import time
from types import TracebackType
from typing import Any, Self

import httpx

from app.config import Settings
from app.config import settings as default_settings
from app.llm.base import BaseLLM
from app.llm.exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from app.llm.models import ChatMessage, LLMHealth, LLMResponse, TokenUsage
from app.llm.retry import RETRYABLE_STATUS_CODES, with_retry

logger = logging.getLogger(__name__)

_USER_AGENT = "DataGuardian-AI/1.0"


class GrokProvider(BaseLLM):
    """xAI Grok, spoken to over the OpenAI-compatible chat-completions API."""

    name = "grok"

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Build the provider.

        Constructing WITHOUT an API key is legal — the app must boot with no
        key so /health can report "unconfigured" honestly. The key is checked
        on first call instead.

        Args:
            settings: Configuration source; defaults to the app singleton.
            transport: Test seam — inject ``httpx.MockTransport`` here.
        """
        self._settings = settings or default_settings
        self._model = self._settings.xai_model
        self._base_url = self._settings.xai_base_url.rstrip("/")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
        }
        if self._settings.xai_api_key:
            headers["Authorization"] = f"Bearer {self._settings.xai_api_key}"

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._settings.llm_timeout),
            headers=headers,
            transport=transport,
        )

    # -- BaseLLM primitives -----------------------------------------------------

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self._require_key()

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in messages
            ],
            "temperature": (
                self._settings.llm_temperature if temperature is None else temperature
            ),
            "max_tokens": (
                self._settings.llm_max_tokens if max_tokens is None else max_tokens
            ),
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        body = await with_retry(
            lambda: self._post_chat(payload),
            attempts=self._settings.llm_max_retries + 1,
            description=f"Grok chat ({self._model})",
        )
        latency_ms = (time.perf_counter() - started) * 1000

        response = self._to_response(body, latency_ms)
        logger.info(
            "Grok completion: model=%s tokens=%d/%d latency=%.0fms finish=%s",
            response.model,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            latency_ms,
            response.finish_reason,
        )
        return response

    async def health(self) -> LLMHealth:
        """Probe the API. Reports state, never raises, spends no tokens.

        Uses ``GET /models`` — it authenticates like any call but bills
        nothing, so it is safe on a poll.
        """
        if not self._settings.xai_api_key:
            return LLMHealth(
                provider=self.name,
                configured=False,
                reachable=False,
                model=self._model,
                error="XAI_API_KEY is not set",
            )

        started = time.perf_counter()
        try:
            response = await self._client.get("/models")
            latency_ms = (time.perf_counter() - started) * 1000
            if response.status_code in (401, 403):
                return LLMHealth(
                    provider=self.name,
                    configured=True,
                    reachable=False,
                    model=self._model,
                    latency_ms=latency_ms,
                    error="XAI_API_KEY was rejected (invalid or expired)",
                )
            if response.status_code >= 400:
                return LLMHealth(
                    provider=self.name,
                    configured=True,
                    reachable=False,
                    model=self._model,
                    latency_ms=latency_ms,
                    error=f"xAI API returned HTTP {response.status_code}",
                )
            return LLMHealth(
                provider=self.name,
                configured=True,
                reachable=True,
                model=self._model,
                latency_ms=latency_ms,
            )
        except httpx.HTTPError as exc:
            return LLMHealth(
                provider=self.name,
                configured=True,
                reachable=False,
                model=self._model,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=f"Could not reach {self._base_url}: {exc}",
            )

    # -- Transport ----------------------------------------------------------------

    async def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        """One POST to /chat/completions with typed error translation."""
        try:
            response = await self._client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"Grok did not respond within {self._settings.llm_timeout}s"
            ) from exc
        except httpx.TransportError as exc:
            raise LLMConnectionError(
                f"Could not reach xAI at {self._base_url}: {exc}"
            ) from exc

        if response.status_code == 429:
            raise LLMRateLimitError("xAI rate limit hit (HTTP 429)")
        if response.status_code in (401, 403):
            raise LLMAuthenticationError(
                f"xAI rejected the request (HTTP {response.status_code}): "
                "XAI_API_KEY is invalid, expired, or lacks access to "
                f"model '{self._model}'"
            )
        if response.status_code in RETRYABLE_STATUS_CODES:
            raise LLMConnectionError(
                f"xAI returned a transient HTTP {response.status_code}"
            )
        if response.status_code >= 400:
            raise LLMResponseError(
                f"xAI returned HTTP {response.status_code}: {_preview(response.text)}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMResponseError(
                f"xAI returned non-JSON: {_preview(response.text)}"
            ) from exc
        if not isinstance(body, dict):
            raise LLMResponseError(
                f"Expected a JSON object from xAI, got {type(body).__name__}"
            )
        return body

    def _to_response(self, body: dict[str, Any], latency_ms: float) -> LLMResponse:
        """Map the OpenAI-compatible completion payload to `LLMResponse`."""
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMResponseError("xAI response contained no choices")

        first: dict[str, Any] = choices[0] if isinstance(choices[0], dict) else {}
        raw_message = first.get("message")
        message: dict[str, Any] = raw_message if isinstance(raw_message, dict) else {}
        text = message.get("content")
        if not isinstance(text, str) or not text.strip():
            raise LLMResponseError("xAI response contained an empty completion")

        raw_usage = body.get("usage")
        usage_raw: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
        return LLMResponse(
            text=text,
            provider=self.name,
            model=str(body.get("model", self._model)),
            usage=TokenUsage(
                prompt_tokens=int(usage_raw.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage_raw.get("completion_tokens", 0) or 0),
            ),
            latency_ms=latency_ms,
            finish_reason=(
                str(first.get("finish_reason"))
                if first.get("finish_reason") is not None
                else None
            ),
        )

    def _require_key(self) -> None:
        if not self._settings.xai_api_key:
            raise LLMConfigurationError(
                "XAI_API_KEY is not set. Create a key at https://console.x.ai "
                "and add it to backend/.env"
            )

    # -- Lifecycle ------------------------------------------------------------------

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()


def _preview(text: str, limit: int = 200) -> str:
    collapsed = " ".join(text.split())
    return collapsed[:limit] + "…" if len(collapsed) > limit else collapsed
