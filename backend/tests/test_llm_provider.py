"""GrokProvider tests.

Every test drives the real provider, retry policy, and parsing code against
`httpx.MockTransport` — only the network is replaced. No real xAI call is
ever made, and no API key is required.
"""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from app.config import Settings
from app.llm import (
    ChatMessage,
    ChatRole,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
)
from app.llm.providers import GrokProvider

Handler = Callable[[httpx.Request], httpx.Response]


def make_provider(
    handler: Handler,
    *,
    api_key: str | None = "test-key",
    retries: int = 0,
) -> GrokProvider:
    """Build a provider whose transport is the supplied handler."""
    settings = Settings(
        xai_api_key=api_key,
        xai_model="grok-4-fast-reasoning",
        xai_base_url="https://api.x.ai/v1",
        llm_max_retries=retries,
        llm_timeout=5.0,
        llm_temperature=0.2,
        llm_max_tokens=512,
    )
    return GrokProvider(settings=settings, transport=httpx.MockTransport(handler))


def completion(
    text: str, *, prompt_tokens: int = 10, completion_tokens: int = 20
) -> dict[str, Any]:
    """A minimal xAI/OpenAI-shaped chat completion."""
    return {
        "id": "chatcmpl-test",
        "model": "grok-4-fast-reasoning",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    }


class TestInitialization:
    def test_builds_without_an_api_key(self) -> None:
        # Startup must never depend on credentials being present.
        provider = make_provider(lambda _r: httpx.Response(200), api_key=None)
        assert provider.name == "grok"

    def test_api_key_becomes_a_bearer_header(self) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return httpx.Response(200, json=completion("ok"))

        provider = make_provider(handler, api_key="secret-key")
        import anyio

        anyio.run(lambda: provider.generate("hi"))
        assert captured["authorization"] == "Bearer secret-key"

    async def test_calling_without_a_key_raises_a_configuration_error(self) -> None:
        provider = make_provider(lambda _r: httpx.Response(200), api_key=None)
        with pytest.raises(LLMConfigurationError) as excinfo:
            await provider.generate("hello")
        # The message must say exactly what to do.
        assert "XAI_API_KEY" in excinfo.value.detail
        assert "console.x.ai" in excinfo.value.detail

    async def test_request_targets_the_chat_completions_endpoint(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=completion("ok"))

        await make_provider(handler).generate("hello")
        assert captured["url"] == "https://api.x.ai/v1/chat/completions"
        assert captured["body"]["model"] == "grok-4-fast-reasoning"


class TestChat:
    async def test_returns_a_typed_response_with_usage(self) -> None:
        provider = make_provider(
            lambda _r: httpx.Response(
                200,
                json=completion("Hello there", prompt_tokens=12, completion_tokens=7),
            )
        )
        response = await provider.chat([ChatMessage(role=ChatRole.USER, content="hi")])

        assert response.text == "Hello there"
        assert response.provider == "grok"
        assert response.usage.prompt_tokens == 12
        assert response.usage.total_tokens == 19
        assert response.latency_ms is not None
        assert response.finish_reason == "stop"

    async def test_settings_supply_temperature_and_max_tokens(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json=completion("ok"))

        await make_provider(handler).generate("hi")
        # Low temperature is a deliberate governance default.
        assert captured["temperature"] == 0.2
        assert captured["max_tokens"] == 512

    async def test_per_call_overrides_beat_settings(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json=completion("ok"))

        await make_provider(handler).generate("hi", temperature=0.9, max_tokens=64)
        assert captured["temperature"] == 0.9
        assert captured["max_tokens"] == 64

    async def test_system_prompt_is_sent_first(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json=completion("ok"))

        await make_provider(handler).generate("question", system="be terse")
        messages = captured["messages"]
        assert messages[0] == {"role": "system", "content": "be terse"}
        assert messages[1] == {"role": "user", "content": "question"}

    async def test_json_mode_sets_response_format(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json=completion("{}"))

        await make_provider(handler).chat(
            [ChatMessage(role=ChatRole.USER, content="x")], json_mode=True
        )
        assert captured["response_format"] == {"type": "json_object"}

    async def test_summarize_uses_a_faithfulness_system_prompt(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json=completion("summary"))

        response = await make_provider(handler).summarize("long content")
        assert response.text == "summary"
        assert "Do not add information" in captured["messages"][0]["content"]


class TestFailureTranslation:
    async def test_connection_failure(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        with pytest.raises(LLMConnectionError) as excinfo:
            await make_provider(handler).generate("hi")
        assert "api.x.ai" in excinfo.value.detail

    async def test_timeout(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow")

        with pytest.raises(LLMTimeoutError) as excinfo:
            await make_provider(handler).generate("hi")
        assert excinfo.value.status_code == 504

    @pytest.mark.parametrize("status_code", [401, 403])
    async def test_rejected_key_is_actionable_and_not_401(
        self, status_code: int
    ) -> None:
        provider = make_provider(lambda _r: httpx.Response(status_code))
        with pytest.raises(LLMAuthenticationError) as excinfo:
            await provider.generate("hi")
        assert "XAI_API_KEY" in excinfo.value.detail
        # 502, not 401 — our caller is not the unauthenticated party.
        assert excinfo.value.status_code == 502

    async def test_empty_completion_is_rejected(self) -> None:
        body = completion("")
        provider = make_provider(lambda _r: httpx.Response(200, json=body))
        with pytest.raises(LLMResponseError, match="empty completion"):
            await provider.generate("hi")

    async def test_missing_choices_is_rejected(self) -> None:
        provider = make_provider(lambda _r: httpx.Response(200, json={"choices": []}))
        with pytest.raises(LLMResponseError, match="no choices"):
            await provider.generate("hi")

    async def test_non_json_body_is_rejected(self) -> None:
        provider = make_provider(
            lambda _r: httpx.Response(200, text="<html>oops</html>")
        )
        with pytest.raises(LLMResponseError, match="non-JSON"):
            await provider.generate("hi")


class TestRetry:
    async def test_rate_limit_is_retried_then_succeeds(self) -> None:
        attempts = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                return httpx.Response(429)
            return httpx.Response(200, json=completion("recovered"))

        settings = Settings(
            xai_api_key="k",
            llm_max_retries=3,
        )
        provider = GrokProvider(
            settings=settings, transport=httpx.MockTransport(handler)
        )
        # Base delays are jittered but tiny at these attempt counts.
        response = await provider.generate("hi")
        assert response.text == "recovered"
        assert attempts == 3

    async def test_auth_failure_is_never_retried(self) -> None:
        attempts = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(401)

        provider = make_provider(handler, retries=5)
        with pytest.raises(LLMAuthenticationError):
            await provider.generate("hi")
        # Deterministic failure: one attempt only.
        assert attempts == 1


class TestHealth:
    async def test_reports_unconfigured_without_a_key(self) -> None:
        health = await make_provider(
            lambda _r: httpx.Response(200), api_key=None
        ).health()

        assert health.configured is False
        assert health.reachable is False
        assert health.error is not None
        assert "XAI_API_KEY" in health.error

    async def test_reports_reachable_when_the_api_answers(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            # A token-free probe: models list, not a completion.
            assert request.url.path.endswith("/models")
            return httpx.Response(200, json={"data": []})

        health = await make_provider(handler).health()
        assert health.configured is True
        assert health.reachable is True
        assert health.model == "grok-4-fast-reasoning"
        assert health.latency_ms is not None

    async def test_reports_rejected_key_distinctly_from_missing_key(self) -> None:
        health = await make_provider(lambda _r: httpx.Response(401)).health()
        assert health.configured is True  # a key exists…
        assert health.reachable is False  # …but was rejected
        assert health.error is not None
        assert "rejected" in health.error

    async def test_health_never_raises_on_network_failure(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route")

        health = await make_provider(handler).health()
        assert health.reachable is False
        assert health.error is not None


class _Answer(BaseModel):
    headline: str
    score: int


class TestStructuredOutput:
    async def test_parses_a_clean_json_object(self) -> None:
        payload = json.dumps({"headline": "All good", "score": 86})
        provider = make_provider(
            lambda _r: httpx.Response(200, json=completion(payload))
        )

        answer = await provider.structured_output("assess", _Answer)
        assert answer.headline == "All good"
        assert answer.score == 86

    async def test_strips_markdown_fences(self) -> None:
        fenced = '```json\n{"headline": "Fenced", "score": 1}\n```'
        provider = make_provider(
            lambda _r: httpx.Response(200, json=completion(fenced))
        )

        answer = await provider.structured_output("assess", _Answer)
        assert answer.headline == "Fenced"

    async def test_ignores_prose_around_the_object(self) -> None:
        chatty = (
            'Sure! Here you go:\n{"headline": "Chatty", "score": 2}\nHope that helps.'
        )
        provider = make_provider(
            lambda _r: httpx.Response(200, json=completion(chatty))
        )

        answer = await provider.structured_output("assess", _Answer)
        assert answer.headline == "Chatty"

    async def test_schema_is_embedded_in_the_request(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json=completion('{"headline": "x", "score": 1}'))

        await make_provider(handler).structured_output("assess", _Answer)
        user_message = captured["messages"][1]["content"]
        assert "headline" in user_message
        assert "score" in user_message
        # JSON mode is requested alongside the schema.
        assert captured["response_format"] == {"type": "json_object"}

    async def test_invalid_json_triggers_exactly_one_repair_attempt(self) -> None:
        calls = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(200, json=completion("not json at all"))
            return httpx.Response(
                200, json=completion('{"headline": "Repaired", "score": 5}')
            )

        answer = await make_provider(handler).structured_output("assess", _Answer)
        assert answer.headline == "Repaired"
        assert calls == 2

    async def test_persistent_schema_failure_propagates(self) -> None:
        # Never silently return bad data: two failures is a real error.
        calls = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json=completion('{"wrong": "shape"}'))

        with pytest.raises(LLMResponseError):
            await make_provider(handler).structured_output("assess", _Answer)
        assert calls == 2  # original + one repair, then give up

    async def test_repair_message_includes_the_validation_error(self) -> None:
        sent: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            sent.append(body)
            if len(sent) == 1:
                return httpx.Response(200, json=completion('{"headline": "x"}'))
            return httpx.Response(200, json=completion('{"headline": "x", "score": 3}'))

        await make_provider(handler).structured_output("assess", _Answer)
        repair_prompt = sent[1]["messages"][-1]["content"]
        # The model is told precisely what was wrong.
        assert "score" in repair_prompt
