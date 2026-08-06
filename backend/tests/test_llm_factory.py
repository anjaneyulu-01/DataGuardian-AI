"""Factory and prompt-system tests.

Neither touches the network: the factory only constructs, and prompts are
pure string templates.
"""

from typing import ClassVar

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.llm import BaseLLM, LLMFactory, LLMProviderNotSupportedError
from app.llm.exceptions import LLMConfigurationError
from app.llm.prompts import (
    PERSONA,
    PromptTemplate,
    documentation,
    governance,
    recommendations,
    reports,
)
from app.llm.providers import FallbackProvider, GroqProvider


class TestFactory:
    def test_default_is_auto_selection(self) -> None:
        # `auto` is the default so swapping which API key you hold needs no
        # code or config change beyond pasting the key.
        assert Settings().llm_provider == "auto"

    def test_auto_picks_the_first_configured_provider(self) -> None:
        settings = Settings(llm_provider="auto", gemini_api_key="k")
        provider = LLMFactory.create(settings)
        assert provider.name == "gemini"

    def test_auto_respects_the_configured_order(self) -> None:
        # Both configured: order decides, not dict iteration order.
        settings = Settings(
            llm_provider="auto",
            groq_api_key="k1",
            gemini_api_key="k2",
            llm_provider_order=["gemini", "groq"],
            llm_fallback_enabled=False,
        )
        assert LLMFactory.create(settings).name == "gemini"

    def test_auto_without_any_key_fails_with_an_actionable_message(self) -> None:
        with pytest.raises(LLMConfigurationError) as excinfo:
            LLMFactory.create(Settings(llm_provider="auto"))
        detail = excinfo.value.detail
        # Must name the variables the user can actually set.
        assert "GROQ_API_KEY" in detail
        assert "GEMINI_API_KEY" in detail

    def test_explicit_grok_selection(self) -> None:
        provider = LLMFactory.create(Settings(llm_provider="grok"))
        assert isinstance(provider, BaseLLM)

    def test_explicit_groq_selection(self) -> None:
        # Groq (inference host) is a different vendor from Grok (xAI), despite
        # the one-letter difference. Selecting each must yield a distinct
        # provider — a registry typo here would be near-invisible in review.
        provider = LLMFactory.create(Settings(llm_provider="groq"))
        assert isinstance(provider, GroqProvider)
        assert provider.name == "groq"

    def test_grok_and_groq_are_not_the_same_provider(self) -> None:
        grok = LLMFactory.create(Settings(llm_provider="grok"))
        groq = LLMFactory.create(Settings(llm_provider="groq"))

        assert type(grok) is not type(groq)
        assert grok.name != groq.name
        # Different endpoints and different credential variables.
        assert "x.ai" in Settings().xai_base_url
        assert "groq.com" in Settings().groq_base_url

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

    @pytest.mark.parametrize(
        "name,key_field",
        [
            ("gemini", "gemini_api_key"),
            ("openai", "openai_api_key"),
            ("claude", "anthropic_api_key"),
        ],
    )
    def test_every_registered_provider_is_implemented(
        self, name: str, key_field: str
    ) -> None:
        # All five are real now — none raise "not implemented".
        settings = Settings(
            **{"llm_provider": name, key_field: "k", "llm_fallback_enabled": False}  # type: ignore[arg-type]
        )
        assert LLMFactory.create(settings).name == name

    def test_supported_providers_covers_the_full_roster(self) -> None:
        assert LLMFactory.supported_providers() == [
            "claude",
            "gemini",
            "grok",
            "groq",
            "openai",
        ]

    @pytest.mark.parametrize(
        "provider_name,key_field",
        [("grok", "xai_api_key"), ("groq", "groq_api_key")],
    )
    def test_factory_does_not_require_an_api_key(
        self, provider_name: str, key_field: str
    ) -> None:
        # The app must boot without credentials so /health can report the
        # unconfigured state honestly.
        settings = Settings(**{"llm_provider": provider_name, key_field: None})  # type: ignore[arg-type]
        provider = LLMFactory.create(settings)
        assert provider.name == provider_name


class TestModelOverride:
    @pytest.mark.parametrize(
        "provider_name,key_field",
        [
            ("groq", "groq_api_key"),
            ("grok", "xai_api_key"),
            ("gemini", "gemini_api_key"),
        ],
    )
    def test_llm_model_overrides_whichever_provider_is_active(
        self, provider_name: str, key_field: str
    ) -> None:
        # One variable changes the model regardless of vendor, so switching
        # models never means hunting for the right provider-specific name.
        settings = Settings(
            **{  # type: ignore[arg-type]
                "llm_provider": provider_name,
                key_field: "k",
                "llm_model": "custom-model-x",
                "llm_fallback_enabled": False,
            }
        )
        assert LLMFactory.create(settings).model == "custom-model-x"

    def test_without_override_the_provider_default_applies(self) -> None:
        settings = Settings(
            llm_provider="groq", groq_api_key="k", llm_fallback_enabled=False
        )
        assert LLMFactory.create(settings).model == Settings().groq_model


class TestAvailabilityAndFallback:
    def test_available_lists_only_providers_with_keys(self) -> None:
        settings = Settings(groq_api_key="k", gemini_api_key="k2")
        assert LLMFactory.available_providers(settings) == ["groq", "gemini"]

    def test_blank_key_does_not_count_as_configured(self) -> None:
        # An empty value in .env is the same as absent.
        assert LLMFactory.available_providers(Settings(groq_api_key="   ")) == []

    def test_second_provider_becomes_a_fallback_chain(self) -> None:
        settings = Settings(llm_provider="auto", groq_api_key="k", gemini_api_key="k2")
        provider = LLMFactory.create(settings)
        assert isinstance(provider, FallbackProvider)
        assert provider.chain == ["groq", "gemini"]
        assert provider.primary.name == "groq"

    def test_single_provider_is_not_wrapped(self) -> None:
        # No point paying for a chain of one.
        provider = LLMFactory.create(Settings(llm_provider="auto", groq_api_key="k"))
        assert not isinstance(provider, FallbackProvider)

    def test_fallback_can_be_disabled(self) -> None:
        settings = Settings(
            llm_provider="auto",
            groq_api_key="k",
            gemini_api_key="k2",
            llm_fallback_enabled=False,
        )
        assert not isinstance(LLMFactory.create(settings), FallbackProvider)

    def test_describe_reports_the_whole_picture(self) -> None:
        settings = Settings(llm_provider="auto", groq_api_key="k", gemini_api_key="k2")
        described = LLMFactory.describe(settings)

        assert described["active"] == "groq"
        assert described["available"] == ["groq", "gemini"]
        assert described["fallback_chain"] == ["gemini"]
        # Names the variable for each provider that is NOT usable, so the
        # health endpoint can tell an operator exactly what to set.
        assert described["missing_keys"] == {
            "grok": "XAI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
        }

    def test_unknown_name_in_order_is_ignored_not_fatal(self) -> None:
        # A typo in LLM_PROVIDER_ORDER must not stop the app booting when a
        # usable provider exists.
        settings = Settings(
            llm_provider="auto",
            groq_api_key="k",
            llm_provider_order=["typo-provider", "groq"],
        )
        assert LLMFactory.create(settings).name == "groq"


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
