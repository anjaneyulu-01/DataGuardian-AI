"""The provider contract.

`BaseLLM` is what every consumer of the LLM layer programs against — the
prompt modules, the API later, the LangGraph agent tomorrow. Nothing outside
`app/llm/providers/` may import a concrete provider.

Division of labour, non-negotiable:

* The **deterministic layers** (Tool layer, rule engine) find datasets, check
  owners, compute risk, traverse lineage. Their output is structured JSON.
* The **LLM** receives that JSON as evidence and only reasons, explains,
  summarizes, documents, and recommends. It never queries DataHub, and it
  never invents facts that are not in the evidence it was handed.

Providers implement two primitives (`chat`, `health`). Everything else —
`generate`, `summarize`, `structured_output` — is built on `chat` here in the
base class, so a new provider is one file implementing two methods.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.exceptions import LLMResponseError
from app.llm.models import ChatMessage, ChatRole, LLMHealth, LLMResponse

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)

# System stance prepended to every structured-output request. States the
# ground rules once so individual prompts do not have to repeat them.
_STRUCTURED_SYSTEM = (
    "You are DataGuardian, a metadata governance engineer. The user message "
    "contains evidence collected by deterministic tooling; treat it as ground "
    "truth. Do not invent assets, owners, numbers, or lineage that are not in "
    "the evidence. Respond with a single JSON object matching the requested "
    "schema — no prose, no markdown fences, no commentary."
)

_SUMMARIZE_SYSTEM = (
    "You are DataGuardian, a metadata governance engineer. Summarize the "
    "supplied content faithfully and concisely for a technical audience. "
    "Do not add information that is not present."
)


class BaseLLM(ABC):
    """Abstract provider. Subclasses implement `chat` and `health` only."""

    #: Stable provider identifier ("grok", "gemini", …).
    name: str = "base"

    # -- Primitives every provider must implement ------------------------------

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Run one chat completion.

        Args:
            messages: Full conversation, including any system message.
            temperature: Override the configured default.
            max_tokens: Override the configured default.
            json_mode: Ask the provider to constrain output to valid JSON.
        """

    @abstractmethod
    async def health(self) -> LLMHealth:
        """Probe the provider. Reports, never raises — mirrors DataHub health."""

    # -- Conveniences built on `chat` -------------------------------------------

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Single-turn completion from a plain prompt."""
        messages: list[ChatMessage] = []
        if system:
            messages.append(ChatMessage(role=ChatRole.SYSTEM, content=system))
        messages.append(ChatMessage(role=ChatRole.USER, content=prompt))
        return await self.chat(messages, temperature=temperature, max_tokens=max_tokens)

    async def summarize(
        self,
        content: str,
        *,
        instruction: str = "Summarize the following for a governance report.",
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Faithful summary of supplied content (findings, run logs, …)."""
        return await self.chat(
            [
                ChatMessage(role=ChatRole.SYSTEM, content=_SUMMARIZE_SYSTEM),
                ChatMessage(
                    role=ChatRole.USER, content=f"{instruction}\n\n---\n{content}"
                ),
            ],
            max_tokens=max_tokens,
        )

    async def structured_output(
        self,
        prompt: str,
        schema: type[TModel],
        *,
        system: str | None = None,
        temperature: float | None = None,
    ) -> TModel:
        """Generate a response validated against a Pydantic model.

        The schema's JSON Schema is embedded in the prompt and the provider is
        asked for JSON mode. If the first response fails validation, ONE repair
        round-trip is made with the validation errors — almost-valid JSON is
        the most common failure mode and a single nudge usually fixes it.
        Beyond that, `LLMResponseError` propagates; hiding persistent schema
        failures would poison downstream consumers with bad data.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        full_system = (
            f"{system.strip()}\n\n{_STRUCTURED_SYSTEM}"
            if system
            else _STRUCTURED_SYSTEM
        )
        request = (
            f"{prompt}\n\n"
            f"Respond with a single JSON object conforming to this JSON Schema:\n"
            f"{schema_json}"
        )

        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=full_system),
            ChatMessage(role=ChatRole.USER, content=request),
        ]

        response = await self.chat(messages, temperature=temperature, json_mode=True)
        try:
            return self._parse_structured(response.text, schema)
        except LLMResponseError as first_error:
            logger.warning(
                "Structured output failed validation on first attempt "
                "(provider=%s, schema=%s): %s — attempting one repair",
                self.name,
                schema.__name__,
                first_error.detail,
            )
            repair = [
                *messages,
                ChatMessage(role=ChatRole.ASSISTANT, content=response.text),
                ChatMessage(
                    role=ChatRole.USER,
                    content=(
                        "That response was invalid: "
                        f"{first_error.detail}\n"
                        "Return ONLY the corrected JSON object. No other text."
                    ),
                ),
            ]
            retried = await self.chat(repair, temperature=temperature, json_mode=True)
            return self._parse_structured(retried.text, schema)

    # -- Shared parsing ----------------------------------------------------------

    @staticmethod
    def _parse_structured(text: str, schema: type[TModel]) -> TModel:
        """Extract and validate a JSON object from model output.

        Tolerates the two classic wrappers — markdown fences and leading
        prose — but nothing more exotic. Central here so every provider gets
        identical behaviour.
        """
        candidate = _extract_json(text)
        if candidate is None:
            raise LLMResponseError(
                f"Model output contained no JSON object (got: {text[:120]!r}…)"
            )
        try:
            parsed: Any = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(f"Model output is not valid JSON: {exc}") from exc
        try:
            return schema.model_validate(parsed)
        except ValidationError as exc:
            # Compact error list — this string is fed back for the repair pass.
            issues = "; ".join(
                f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}"
                for error in exc.errors()[:5]
            )
            raise LLMResponseError(
                f"JSON does not match schema {schema.__name__}: {issues}"
            ) from exc


def _extract_json(text: str) -> str | None:
    """Pull the outermost JSON object out of possibly-wrapped model output."""
    stripped = text.strip()
    # ```json … ``` fences.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fence:
        return fence.group(1)
    # Bare object, possibly with prose around it: take first '{' to last '}'.
    start, end = stripped.find("{"), stripped.rfind("}")
    if start != -1 and end > start:
        return stripped[start : end + 1]
    return None
