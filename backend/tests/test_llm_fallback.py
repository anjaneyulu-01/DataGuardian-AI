"""Fail-over behaviour.

The whole value of the chain rests on one distinction: transient failures roll
over to the next vendor, deterministic ones do not. Getting that backwards
either hides a real misconfiguration or wastes every provider's quota on a
request that could never succeed.
"""

import pytest

from app.llm.base import BaseLLM
from app.llm.exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from app.llm.models import ChatMessage, ChatRole, LLMHealth, LLMResponse, TokenUsage
from app.llm.providers import FallbackProvider


class StubProvider(BaseLLM):
    """A provider that answers, or fails with a chosen exception."""

    def __init__(
        self, provider_name: str, error: Exception | None = None, reply: str = "ok"
    ) -> None:
        self.name = provider_name  # type: ignore[misc]
        self._error = error
        self._reply = reply
        self.calls = 0
        self.closed = False

    @property
    def model(self) -> str:
        return f"{self.name}-model"

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return LLMResponse(
            text=self._reply,
            provider=self.name,
            model=self.model,
            usage=TokenUsage(),
            latency_ms=1.0,
        )

    async def health(self) -> LLMHealth:
        return LLMHealth(
            provider=self.name, configured=True, reachable=True, model=self.model
        )

    async def aclose(self) -> None:
        self.closed = True


def ask() -> list[ChatMessage]:
    return [ChatMessage(role=ChatRole.USER, content="hi")]


class TestFailOver:
    async def test_primary_answers_and_others_are_untouched(self) -> None:
        primary = StubProvider("groq", reply="from-primary")
        backup = StubProvider("gemini")

        response = await FallbackProvider([primary, backup]).chat(ask())

        assert response.text == "from-primary"
        assert primary.calls == 1
        assert backup.calls == 0  # never woken unnecessarily

    @pytest.mark.parametrize(
        "transient",
        [
            LLMRateLimitError("429"),
            LLMConnectionError("down"),
            LLMTimeoutError("slow"),
        ],
    )
    async def test_transient_failure_rolls_over(self, transient: Exception) -> None:
        # A different vendor has a different quota and a different outage, so
        # trying the next one is genuinely likely to work.
        primary = StubProvider("groq", error=transient)
        backup = StubProvider("gemini", reply="from-backup")

        response = await FallbackProvider([primary, backup]).chat(ask())

        assert response.text == "from-backup"
        assert primary.calls == 1
        assert backup.calls == 1

    @pytest.mark.parametrize(
        "deterministic",
        [
            LLMAuthenticationError("bad key"),
            LLMResponseError("garbage"),
            LLMConfigurationError("no key"),
        ],
    )
    async def test_deterministic_failure_does_not_roll_over(
        self, deterministic: Exception
    ) -> None:
        # Rolling over here would burn the backup's quota AND hide the real
        # error behind a second, unrelated one.
        primary = StubProvider("groq", error=deterministic)
        backup = StubProvider("gemini")

        with pytest.raises(type(deterministic)):
            await FallbackProvider([primary, backup]).chat(ask())

        assert backup.calls == 0

    async def test_rolls_through_several_providers(self) -> None:
        a = StubProvider("groq", error=LLMRateLimitError("429"))
        b = StubProvider("gemini", error=LLMConnectionError("down"))
        c = StubProvider("openai", reply="third-time-lucky")

        response = await FallbackProvider([a, b, c]).chat(ask())

        assert response.text == "third-time-lucky"
        assert (a.calls, b.calls, c.calls) == (1, 1, 1)

    async def test_all_transient_raises_the_last_error(self) -> None:
        # The caller still gets a typed, retryable error rather than a
        # synthetic wrapper.
        a = StubProvider("groq", error=LLMRateLimitError("429"))
        b = StubProvider("gemini", error=LLMTimeoutError("slow"))

        with pytest.raises(LLMTimeoutError):
            await FallbackProvider([a, b]).chat(ask())

    async def test_empty_chain_is_rejected_at_construction(self) -> None:
        with pytest.raises(LLMConfigurationError, match="at least one provider"):
            FallbackProvider([])


class TestChainMetadata:
    async def test_health_reports_primary_and_names_the_chain(self) -> None:
        chain = FallbackProvider(
            [StubProvider("groq"), StubProvider("gemini"), StubProvider("openai")]
        )
        health = await chain.health()

        assert health.provider == "groq"
        assert health.fallback_chain == ["gemini", "openai"]

    def test_model_reports_the_primary_model(self) -> None:
        chain = FallbackProvider([StubProvider("groq"), StubProvider("gemini")])
        assert chain.model == "groq-model"
        assert chain.chain == ["groq", "gemini"]

    async def test_aclose_releases_every_provider(self) -> None:
        # A leaked httpx client per provider would exhaust sockets over time.
        providers = [StubProvider("groq"), StubProvider("gemini")]
        await FallbackProvider(providers).aclose()
        assert all(p.closed for p in providers)
