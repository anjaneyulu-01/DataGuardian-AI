"""Typed results returned by the LLM layer.

Everything a provider produces is wrapped in one of these models. Callers —
the API later, the LangGraph agent tomorrow — never touch a raw provider
payload, exactly as they never touch raw GraphQL from DataHub.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(_Base):
    """One turn of a conversation, provider-agnostic."""

    role: ChatRole
    content: str


class TokenUsage(_Base):
    """Token accounting, for cost visibility in logs and reports."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMResponse(_Base):
    """The universal envelope for a completed generation."""

    text: str
    provider: str
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float | None = None
    finish_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LLMHealth(_Base):
    """Result of the provider connectivity probe. Never raised, reported.

    Mirrors `DataHubHealth`: `configured=False` (no API key) is a different,
    more actionable state than `reachable=False` (network/provider outage).
    """

    provider: str
    configured: bool
    reachable: bool
    model: str
    latency_ms: float | None = None
    error: str | None = None
    # Providers that would be tried if this one fails transiently, in order.
    # Empty when fail-over is disabled or nothing else is configured.
    fallback_chain: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Structured outputs the agent asks for by schema
# ---------------------------------------------------------------------------


class Severity(StrEnum):
    """Mirror of the governance severity scale used across the product."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskExplanation(_Base):
    """LLM-written explanation of a risk the rule engine already detected.

    The severity arrives as *input* from the deterministic layer and is echoed
    back so the object is self-contained — the LLM never chooses it.
    """

    asset_urn: str
    asset_name: str
    severity: Severity
    headline: str = Field(description="One-sentence summary of the risk.")
    explanation: str = Field(description="What is wrong, in plain language.")
    business_impact: str = Field(
        description="What breaks for the business if this is left unfixed."
    )
    blast_radius: str = Field(
        description="Downstream exposure, grounded in the supplied lineage."
    )
    next_steps: list[str] = Field(default_factory=list)


class Recommendation(_Base):
    """A single corrective action the LLM proposes from supplied evidence."""

    action: str = Field(
        description="Imperative, specific: 'Assign finance-data as owner'."
    )
    target_urn: str
    rationale: str
    priority: Severity = Severity.MEDIUM
    effort: str | None = Field(
        default=None, description="Rough effort: 'one click', 'requires review', …"
    )


class ReportSection(_Base):
    """One titled section of a structured report."""

    title: str
    body: str


class StructuredReport(_Base):
    """A multi-section governance report (daily digest, weekly summary…)."""

    title: str
    executive_summary: str
    sections: list[ReportSection] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
