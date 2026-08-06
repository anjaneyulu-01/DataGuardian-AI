"""Shared implementation for OpenAI-compatible chat-completions APIs.

A growing number of providers expose the exact same wire protocol as OpenAI's
``/chat/completions`` endpoint — xAI (Grok), Groq, Together, Fireworks,
OpenAI itself. Only three things differ between them:

* the base URL,
* the API key and the environment variable it comes from,
* the default model name.

Everything else — payload construction, retry classification, error
translation, response mapping, the token-free health probe — is identical.
That shared behaviour lives here exactly once. A concrete provider is a
subclass supplying `ProviderConfig`; it contains no transport logic, which is
why adding one is a ~20-line file.

Subclasses must NOT override the transport methods. If a provider needs a
genuinely different protocol (Gemini's `generateContent`, Anthropic's
`/v1/messages`), it implements `BaseLLM` directly instead of subclassing this.
"""

import logging
import time
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ProviderConfig:
    """Everything that distinguishes one OpenAI-compatible vendor from another."""

    #: Human-readable vendor name, used in log lines and error messages.
    vendor: str
    #: Environment variable holding the key, named in errors so the fix is obvious.
    key_env_var: str
    #: Where the user obtains a key, included in the configuration error.
    console_url: str
    api_key: str | None
    base_url: str
    model: str


class OpenAICompatibleProvider(BaseLLM):
    """Base for any vendor speaking the OpenAI chat-completions protocol."""

    def __init__(
        self,
        config: ProviderConfig,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Build the provider.

        Constructing WITHOUT an API key is legal — the app must boot with no
        key so /health can report "unconfigured" honestly. The key is checked
        on first call instead.

        Args:
            config: Vendor-specific endpoint and credential details.
            settings: Configuration source; defaults to the app singleton.
            transport: Test seam — inject ``httpx.MockTransport`` here.
        """
        self._config = config
        self._settings = settings or default_settings
        self._model = config.model
        self._base_url = config.base_url.rstrip("/")

        headers = {"Content-Type": "application/json", "User-Agent": _USER_AGENT}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._settings.llm_timeout),
            headers=headers,
            transport=transport,
        )

    @property
    def model(self) -> str:
        """The model this provider will call."""
        return self._model

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
            description=f"{self._config.vendor} chat ({self._model})",
        )
        latency_ms = (time.perf_counter() - started) * 1000

        response = self._to_response(body, latency_ms)
        logger.info(
            "%s completion: model=%s tokens=%d/%d latency=%.0fms finish=%s",
            self._config.vendor,
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
        if not self._config.api_key:
            return LLMHealth(
                provider=self.name,
                configured=False,
                reachable=False,
                model=self._model,
                error=f"{self._config.key_env_var} is not set",
            )

        started = time.perf_counter()
        try:
            response = await self._client.get("/models")
            latency_ms = (time.perf_counter() - started) * 1000

            if response.status_code in (401, 403):
                return self._unhealthy(
                    latency_ms,
                    f"{self._config.key_env_var} was rejected (invalid or expired)",
                )
            if response.status_code >= 400:
                return self._unhealthy(
                    latency_ms,
                    f"{self._config.vendor} API returned HTTP {response.status_code}",
                )
            return LLMHealth(
                provider=self.name,
                configured=True,
                reachable=True,
                model=self._model,
                latency_ms=latency_ms,
            )
        except httpx.HTTPError as exc:
            return self._unhealthy(
                (time.perf_counter() - started) * 1000,
                f"Could not reach {self._base_url}: {exc}",
            )

    def _unhealthy(self, latency_ms: float, error: str) -> LLMHealth:
        return LLMHealth(
            provider=self.name,
            configured=True,
            reachable=False,
            model=self._model,
            latency_ms=latency_ms,
            error=error,
        )

    # -- Transport ----------------------------------------------------------------

    async def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        """One POST to /chat/completions with typed error translation."""
        vendor = self._config.vendor
        try:
            response = await self._client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"{vendor} did not respond within {self._settings.llm_timeout}s"
            ) from exc
        except httpx.TransportError as exc:
            raise LLMConnectionError(
                f"Could not reach {vendor} at {self._base_url}: {exc}"
            ) from exc

        if response.status_code == 429:
            raise LLMRateLimitError(f"{vendor} rate limit hit (HTTP 429)")
        if response.status_code in (401, 403):
            raise LLMAuthenticationError(
                f"{vendor} rejected the request (HTTP {response.status_code}): "
                f"{self._config.key_env_var} is invalid, expired, or lacks "
                f"access to model '{self._model}'"
            )
        if response.status_code in RETRYABLE_STATUS_CODES:
            raise LLMConnectionError(
                f"{vendor} returned a transient HTTP {response.status_code}"
            )
        if response.status_code >= 400:
            raise LLMResponseError(
                f"{vendor} returned HTTP {response.status_code}: "
                f"{_preview(response.text)}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMResponseError(
                f"{vendor} returned non-JSON: {_preview(response.text)}"
            ) from exc
        if not isinstance(body, dict):
            raise LLMResponseError(
                f"Expected a JSON object from {vendor}, got {type(body).__name__}"
            )
        return body

    def _to_response(self, body: dict[str, Any], latency_ms: float) -> LLMResponse:
        """Map the OpenAI-compatible completion payload to `LLMResponse`."""
        vendor = self._config.vendor
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMResponseError(f"{vendor} response contained no choices")

        first: dict[str, Any] = choices[0] if isinstance(choices[0], dict) else {}
        raw_message = first.get("message")
        message: dict[str, Any] = raw_message if isinstance(raw_message, dict) else {}
        text = message.get("content")
        finish_reason = first.get("finish_reason")

        if not isinstance(text, str) or not text.strip():
            # Reasoning models (Gemini 2.5, Grok 4, o-series) spend part of the
            # budget on internal thinking before emitting visible text. Hitting
            # the cap first yields finish_reason="length" with empty content —
            # a configuration problem, not a provider fault, so say so.
            if finish_reason == "length":
                raise LLMResponseError(
                    f"{vendor} returned an empty completion because the token "
                    f"limit was reached before any visible output "
                    f"(model '{self._model}' spent the budget on internal "
                    f"reasoning). Raise LLM_MAX_TOKENS above "
                    f"{self._settings.llm_max_tokens}, or choose a "
                    "non-reasoning model."
                )
            raise LLMResponseError(
                f"{vendor} response contained an empty completion "
                f"(finish_reason={finish_reason!r})"
            )

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
            finish_reason=str(finish_reason) if finish_reason is not None else None,
        )

    def _require_key(self) -> None:
        if not self._config.api_key:
            raise LLMConfigurationError(
                f"{self._config.key_env_var} is not set. Create a key at "
                f"{self._config.console_url} and add it to the .env file at "
                "the repository root."
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
