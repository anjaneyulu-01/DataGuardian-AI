"""Risk engine tests.

The engine is the agent's factual foundation: if scoring is wrong, every
explanation built on it is confidently wrong. These tests are pure functions
in, models out — no graph, no network, no LLM.
"""

import pytest

from app.agents.risk_engine import (
    RULES,
    RiskEngine,
    has_pii_tag,
    looks_like_pii,
    score_to_level,
)
from app.agents.state import RiskLevel


def dataset(**overrides: object) -> dict:
    """A fully-governed dataset. Tests remove fields to trigger rules."""
    base = {
        "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,fct_orders,PROD)",
        "name": "fct_orders",
        "owners": [{"urn": "urn:li:corpuser:ana", "display_name": "Ana"}],
        "description": "Order facts, one row per order.",
        "tags": [],
        "downstream_count": 0,
        "schema_metadata": {"fields": [{"field_path": "order_id"}]},
    }
    base.update(overrides)
    return base


class TestIndividualRules:
    def test_clean_dataset_scores_zero(self) -> None:
        assessment = RiskEngine().assess_dataset(dataset())
        assert assessment.score == 0
        assert assessment.level is RiskLevel.LOW
        assert assessment.findings == []

    def test_missing_owner(self) -> None:
        assessment = RiskEngine().assess_dataset(dataset(owners=[]))
        assert assessment.triggered_rules == ["missing_owner"]
        assert assessment.score == RULES["missing_owner"].points

    def test_missing_documentation(self) -> None:
        assessment = RiskEngine().assess_dataset(dataset(description=None))
        assert assessment.triggered_rules == ["missing_documentation"]

    def test_blank_description_counts_as_missing(self) -> None:
        # Whitespace is not documentation.
        assessment = RiskEngine().assess_dataset(dataset(description="   "))
        assert "missing_documentation" in assessment.triggered_rules

    def test_untagged_pii(self) -> None:
        assessment = RiskEngine().assess_dataset(
            dataset(
                schema_metadata={
                    "fields": [{"field_path": "order_id"}, {"field_path": "email"}]
                }
            )
        )
        assert "untagged_pii" in assessment.triggered_rules
        pii = next(f for f in assessment.findings if f.rule == "untagged_pii")
        assert "email" in pii.detail

    def test_pii_tag_suppresses_the_finding(self) -> None:
        # Already classified — flagging it again would be noise.
        assessment = RiskEngine().assess_dataset(
            dataset(
                tags=[{"name": "PII"}],
                schema_metadata={"fields": [{"field_path": "email"}]},
            )
        )
        assert "untagged_pii" not in assessment.triggered_rules

    def test_large_downstream_impact(self) -> None:
        assessment = RiskEngine().assess_dataset(dataset(downstream_count=9))
        assert "large_downstream_impact" in assessment.triggered_rules

    def test_downstream_below_threshold_does_not_trigger(self) -> None:
        assessment = RiskEngine().assess_dataset(dataset(downstream_count=2))
        assert "large_downstream_impact" not in assessment.triggered_rules

    def test_deprecated_only_counts_when_still_consumed(self) -> None:
        # A deprecated asset nobody reads is a tidy retirement, not a finding.
        retired = RiskEngine().assess_dataset(
            dataset(deprecation={"deprecated": True}, downstream_count=0)
        )
        assert "deprecated_in_use" not in retired.triggered_rules

        in_use = RiskEngine().assess_dataset(
            dataset(deprecation={"deprecated": True}, downstream_count=3)
        )
        assert "deprecated_in_use" in in_use.triggered_rules

    def test_schema_drift_requires_an_explicit_signal(self) -> None:
        # Never guessed: a fabricated drift finding is worse than a missed one.
        assert (
            "schema_drift" not in RiskEngine().assess_dataset(dataset()).triggered_rules
        )
        assert (
            "schema_drift"
            in RiskEngine().assess_dataset(dataset(schema_drift=True)).triggered_rules
        )


class TestScoring:
    def test_points_are_additive_and_auditable(self) -> None:
        # A reader must be able to add the points up by hand.
        assessment = RiskEngine().assess_dataset(
            dataset(owners=[], description=None, downstream_count=8)
        )
        expected = (
            RULES["missing_owner"].points
            + RULES["missing_documentation"].points
            + RULES["large_downstream_impact"].points
        )
        assert assessment.score == expected
        assert sum(f.points for f in assessment.findings) == expected

    def test_score_is_capped_at_100(self) -> None:
        assessment = RiskEngine().assess_dataset(
            dataset(
                owners=[],
                description=None,
                downstream_count=20,
                deprecation={"deprecated": True},
                schema_drift=True,
                schema_metadata={
                    "fields": [{"field_path": "email"}, {"field_path": "ssn"}]
                },
            )
        )
        assert assessment.score == 100
        assert assessment.level is RiskLevel.CRITICAL

    @pytest.mark.parametrize(
        "score,expected",
        [
            (0, RiskLevel.LOW),
            (19, RiskLevel.LOW),
            (20, RiskLevel.MEDIUM),
            (39, RiskLevel.MEDIUM),
            (40, RiskLevel.HIGH),
            (69, RiskLevel.HIGH),
            (70, RiskLevel.CRITICAL),
            (100, RiskLevel.CRITICAL),
        ],
    )
    def test_band_boundaries(self, score: int, expected: RiskLevel) -> None:
        assert score_to_level(score) is expected

    def test_scoring_is_reproducible(self) -> None:
        # The property an LLM cannot offer: identical input, identical output.
        sample = dataset(owners=[], description=None)
        runs = [RiskEngine().assess_dataset(sample).score for _ in range(20)]
        assert len(set(runs)) == 1


class TestCatalogueScoring:
    def test_catalogue_score_is_the_worst_asset_not_the_sum(self) -> None:
        # Summing would make a large tidy catalogue look worse than a small
        # dangerous one, inverting the steward's priority.
        assessment = RiskEngine().assess_many(
            [dataset(), dataset(), dataset(owners=[], description=None)]
        )
        expected_worst = (
            RULES["missing_owner"].points + RULES["missing_documentation"].points
        )
        assert assessment.score == expected_worst

    def test_findings_accumulate_across_assets(self) -> None:
        assessment = RiskEngine().assess_many(
            [dataset(name="a", owners=[]), dataset(name="b", description=None)]
        )
        assert len(assessment.findings) == 2
        assert {f.asset_name for f in assessment.findings} == {"a", "b"}

    def test_empty_catalogue_is_low_risk_not_an_error(self) -> None:
        assessment = RiskEngine().assess_many([])
        assert assessment.score == 0
        assert assessment.level is RiskLevel.LOW


class TestPIIDetection:
    @pytest.mark.parametrize(
        "column",
        [
            "email",
            "user_email",
            "phone_number",
            "ssn",
            "date_of_birth",
            "dob",
            "home_address",
            "customer_first_name",
            "credit_card_number",
            "passport",
            "national_id",
        ],
    )
    def test_detects_common_pii_columns(self, column: str) -> None:
        assert looks_like_pii(column)

    @pytest.mark.parametrize(
        "column", ["order_id", "created_at", "emailer_job_id", "quantity", "status"]
    )
    def test_does_not_flag_ordinary_columns(self, column: str) -> None:
        # `emailer_job_id` is the interesting one: substring matching would
        # flag it and erode trust in the rule.
        assert not looks_like_pii(column)

    @pytest.mark.parametrize("tag", ["PII", "pii-sensitive", "GDPR", "Confidential"])
    def test_recognises_classification_tags(self, tag: str) -> None:
        assert has_pii_tag([tag])

    def test_unrelated_tags_do_not_count_as_classification(self) -> None:
        assert not has_pii_tag(["tier-1", "certified", "finance"])


class TestLineageIntegration:
    def test_live_lineage_overrides_the_dataset_hint(self) -> None:
        # Real lineage is authoritative; the hint may be stale.
        assessment = RiskEngine().assess_dataset(
            dataset(downstream_count=0),
            lineage={"downstream": {"total": 12}},
        )
        assert "large_downstream_impact" in assessment.triggered_rules

    def test_threshold_is_configurable(self) -> None:
        strict = RiskEngine(downstream_threshold=2)
        assert (
            "large_downstream_impact"
            in strict.assess_dataset(dataset(downstream_count=2)).triggered_rules
        )
