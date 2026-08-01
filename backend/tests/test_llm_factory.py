"""Factory and prompt-system tests.

Neither touches the network: the factory only constructs, and prompts are
pure string templates.
"""

from typing import ClassVar

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.llm import BaseLLM, LLMFactory, LLMProviderNotSupportedError
from app.llm.prompts import (
    PERSONA,
    PromptTemplate,
    documentation,
    governance,
    recommendations,
    reports,
)
from app.llm.providers import GrokProvider


class TestFactory:
    def test_default_provider_is_grok(self) -> None:
        provider = LLMFactory.create(Settings())
        assert isinstance(provider, GrokProvider)
        assert provider.name == "grok"

    def test_explicit_grok_selection(self) -> None:
        provider = LLMFactory.create(Settings(llm_provider="grok"))
        assert isinstance(provider, BaseLLM)

    def test_unknown_provider_is_rejected_at_config_load(self) -> None:
        # `llm_provider` is a Literal, so a typo in .env fails when Settings is
        # constructed — at startup, with a message naming the valid values —
        # rather than at the first LLM call.
        with pytest.raises(ValidationError) as excinfo:
            Settings(llm_provider="llama")  # type: ignore[arg-type]
        assert "grok" in str(excinfo.value)

    def test_factory_still_guards_against_unknown_names(self) -> None:
        # Defence in depth: `model_construct` bypasses validation, standing in
        # for any future path that hands the factory an unvalidated name.
        settings = Settings.model_construct(llm_provider="llama")  # type: ignore[arg-type]
        with pytest.raises(LLMProviderNotSupportedError) as excinfo:
            LLMFactory.create(settings)
        assert "grok" in excinfo.value.detail

    def test_provider_name_is_normalised(self) -> None:
        # Whitespace/case tolerance for any non-Settings caller.
        settings = Settings.model_construct(llm_provider="  GROK  ")  # type: ignore[arg-type]
        assert LLMFactory.create(settings).name == "grok"

    @pytest.mark.parametrize("name", ["gemini", "openai", "claude"])
    def test_placeholder_providers_fail_with_an_actionable_message(
        self, name: str
    ) -> None:
        # Registered but unimplemented: the error must say what to do, not
        # just "unknown".
        with pytest.raises(LLMProviderNotSupportedError) as excinfo:
            LLMFactory.create(Settings(llm_provider=name))  # type: ignore[arg-type]

        detail = excinfo.value.detail
        assert name in detail
        assert "not implemented" in detail
        assert "LLM_PROVIDER=grok" in detail

    def test_supported_providers_covers_the_full_roster(self) -> None:
        assert LLMFactory.supported_providers() == [
            "claude",
            "gemini",
            "grok",
            "openai",
        ]

    def test_factory_does_not_require_an_api_key(self) -> None:
        # The app must boot without credentials so /health can report the
        # unconfigured state honestly.
        provider = LLMFactory.create(Settings(xai_api_key=None))
        assert isinstance(provider, GrokProvider)


class TestPromptTemplate:
    def test_placeholders_are_discovered_from_the_template(self) -> None:
        template = PromptTemplate(
            name="t", system="s", template="Hello {name}, see {evidence}"
        )
        assert template.required == frozenset({"name", "evidence"})

    def test_render_fills_placeholders(self) -> None:
        template = PromptTemplate(name="t", system="s", template="A {x} B")
        assert template.render(x="1") == "A 1 B"

    def test_missing_placeholder_fails_loudly(self) -> None:
        # A silently unfilled `{evidence}` would send the model a prompt with
        # a literal hole in it — worse than an exception.
        template = PromptTemplate(name="t", system="s", template="{a} {b}")
        with pytest.raises(KeyError, match="missing placeholders"):
            template.render(a="1")

    def test_unknown_placeholder_fails_loudly(self) -> None:
        # Catches a renamed variable at the call site.
        template = PromptTemplate(name="t", system="s", template="{a}")
        with pytest.raises(KeyError, match="unknown placeholders"):
            template.render(a="1", typo="2")


class TestPromptLibrary:
    ALL_PROMPTS: ClassVar[list[PromptTemplate]] = [
        governance.RISK_EXPLANATION,
        governance.GOVERNANCE_ANALYSIS,
        governance.MISSING_OWNER_ANALYSIS,
        governance.LINEAGE_EXPLANATION,
        governance.PII_EXPLANATION,
        documentation.README_GENERATION,
        documentation.DATASET_DOCUMENTATION,
        documentation.BUSINESS_DESCRIPTION,
        documentation.SQL_EXPLANATION,
        reports.EXECUTIVE_SUMMARY,
        reports.DAILY_REPORT,
        reports.WEEKLY_REPORT,
        recommendations.CORRECTIVE_ACTIONS,
        recommendations.OWNER_RECOMMENDATION,
        recommendations.TAG_RECOMMENDATION,
        recommendations.GOVERNANCE_SUGGESTIONS,
    ]

    def test_every_prompt_is_loadable_and_named(self) -> None:
        assert len(self.ALL_PROMPTS) == 16
        for prompt in self.ALL_PROMPTS:
            assert prompt.name
            assert "." in prompt.name  # module-qualified, e.g. "governance.pii"

    def test_every_prompt_carries_the_persona(self) -> None:
        # One voice across the product; PERSONA is the single place to edit it.
        for prompt in self.ALL_PROMPTS:
            assert PERSONA in prompt.system, prompt.name

    def test_every_prompt_takes_evidence(self) -> None:
        # The core architectural guarantee: prompts consume structured
        # evidence from the Tool layer rather than asking the model to recall
        # facts.
        for prompt in self.ALL_PROMPTS:
            assert "evidence" in prompt.required, prompt.name

    def test_prompts_render_with_their_declared_placeholders(self) -> None:
        for prompt in self.ALL_PROMPTS:
            values = {key: f"<{key}>" for key in prompt.required}
            rendered = prompt.render(**values)
            assert "<evidence>" in rendered

    def test_prompt_names_are_unique(self) -> None:
        names = [prompt.name for prompt in self.ALL_PROMPTS]
        assert len(names) == len(set(names))
