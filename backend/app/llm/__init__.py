"""Model-agnostic LLM layer.

Layering:

    factory.py    LLM_PROVIDER -> concrete BaseLLM
    base.py       The contract + shared conveniences (generate/summarize/
                  structured_output built on chat)
    providers/    One module per vendor (grok implemented; others planned)
    prompts/      Every prompt in the product, as reviewable templates
    models.py     Typed results (LLMResponse, RiskExplanation, ...)
    retry.py      Transient-failure policy
    exceptions.py Typed failures -> HTTP status

Ground rule enforced by this design: the LLM only reasons over structured
evidence produced by the Tool layer. It never queries DataHub.
"""

from app.llm.base import BaseLLM
from app.llm.exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMError,
    LLMProviderNotSupportedError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from app.llm.factory import LLMFactory
from app.llm.models import (
    ChatMessage,
    ChatRole,
    LLMHealth,
    LLMResponse,
    Recommendation,
    ReportSection,
    RiskExplanation,
    Severity,
    StructuredReport,
    TokenUsage,
)

__all__ = [
    "BaseLLM",
    "ChatMessage",
    "ChatRole",
    "LLMAuthenticationError",
    "LLMConfigurationError",
    "LLMConnectionError",
    "LLMError",
    "LLMFactory",
    "LLMHealth",
    "LLMProviderNotSupportedError",
    "LLMRateLimitError",
    "LLMResponse",
    "LLMResponseError",
    "LLMTimeoutError",
    "Recommendation",
    "ReportSection",
    "RiskExplanation",
    "Severity",
    "StructuredReport",
    "TokenUsage",
]
