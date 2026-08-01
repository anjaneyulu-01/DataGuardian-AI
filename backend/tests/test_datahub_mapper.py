"""Mapper tests.

Pure dict-in / model-out, so these are the cheapest and most valuable tests in
the suite: they pin down exactly how sparse and malformed DataHub metadata is
interpreted.
"""

from datetime import UTC, datetime

from app.integrations.datahub import mapper
from app.integrations.datahub.models import LineageDirection, OwnerKind, TimeRange
from tests import fixtures


class TestSafeHelpers:
    def test_dig_returns_none_instead_of_raising(self) -> None:
        assert mapper._dig({"a": {"b": 1}}, "a", "b") == 1
        assert mapper._dig({"a": None}, "a", "b") is None
        assert mapper._dig(None, "a") is None
        assert mapper._dig({"a": "scalar"}, "a", "b") is None

    def test_text_treats_blank_as_absent(self) -> None:
        # DataHub commonly stores an empty description, which for governance
        # purposes is the same as having none.
        assert mapper._text("   ") is None
        assert mapper._text("  hello  ") == "hello"
        assert mapper._text(None) is None
        assert mapper._text(123) is None

    def test_timestamp_rejects_the_zero_sentinel(self) -> None:
        # 0 means "never" in DataHub; mapping it to 1970 would make every
        # untouched asset look ancient to the staleness rules.
        assert mapper._timestamp(0) is None
        assert mapper._timestamp(None) is None
        assert mapper._timestamp(1735689600000) == datetime(2025, 1, 1, tzinfo=UTC)

    def test_int_tolerates_strings_and_rejects_bools(self) -> None:
        assert mapper._int("42") == 42
        assert mapper._int(42) == 42
        assert mapper._int("not a number") is None
        # bool is an int subclass in Python; a True count would be nonsense.
        assert mapper._int(True) is None


class TestOwners:
    def test_maps_user_and_group_owners(self) -> None:
        owners = mapper.map_owners(fixtures.DATASET_COMPLETE["ownership"])
        by_urn = {o.urn: o for o in owners}

        user = by_urn["urn:li:corpuser:aditi"]
        assert user.kind is OwnerKind.USER
        assert user.name == "aditi"
        # Editable display name wins over the ingested one.
        assert user.display_name == "Aditi (Data Eng)"
        assert user.email == "aditi@example.invalid"
        assert user.ownership_type == "Technical Owner"

        group = by_urn["urn:li:corpGroup:platform"]
        assert group.kind is OwnerKind.GROUP
        assert group.name == "platform"

    def test_deduplicates_a_principal_with_two_ownership_types(self) -> None:
        owners = mapper.map_owners(fixtures.DATASET_COMPLETE["ownership"])
        urns = [o.urn for o in owners]
        assert urns.count("urn:li:corpuser:aditi") == 1
        assert len(owners) == 2

    def test_missing_ownership_yields_empty_list(self) -> None:
        assert mapper.map_owners(None) == []
        assert mapper.map_owners({}) == []
        assert mapper.map_owners({"owners": None}) == []

    def test_owner_without_urn_is_skipped(self) -> None:
        raw = {"owners": [{"owner": {"__typename": "CorpUser", "urn": None}}]}
        assert mapper.map_owners(raw) == []

    def test_aggregations_keep_dangling_owner_references(self) -> None:
        owners = mapper.map_owner_aggregations(
            fixtures.OWNER_AGGREGATIONS["aggregateAcrossEntities"]
        )
        by_urn = {o.urn: o for o in owners}

        assert by_urn["urn:li:corpuser:aditi"].asset_count == 12
        # The entity did not resolve, but the URN and count are still useful —
        # a broken owner reference is itself worth flagging.
        departed = by_urn["urn:li:corpuser:departed"]
        assert departed.asset_count == 3
        assert departed.kind is OwnerKind.USER  # inferred from the URN prefix


class TestDatasets:
    def test_maps_a_complete_dataset(self) -> None:
        dataset = mapper.map_dataset(fixtures.DATASET_COMPLETE)
        assert dataset is not None
        assert dataset.name == "fct_users"
        assert dataset.qualified_name == "prod.analytics.fct_users"
        # editableProperties.description overrides properties.description.
        assert dataset.description == "Curated user fact table."
        assert dataset.platform is not None
        assert dataset.platform.display_name == "Hive"
        assert dataset.domain is not None
        assert dataset.domain.name == "Analytics"
        assert [t.name for t in dataset.tags] == ["PII"]
        assert dataset.custom_properties == {"retention_days": "90", "pii": "true"}
        assert dataset.schema_metadata is not None
        assert dataset.schema_metadata.field_count == 2
        assert dataset.schema_metadata.primary_keys == ["user_id"]
        assert [t.name for t in dataset.glossary_terms] == ["Customer Data"]
        assert dataset.institutional_memory[0].description == "Runbook"

    def test_maps_a_dataset_with_nothing_populated(self) -> None:
        # The governance case: this must map cleanly, not raise.
        dataset = mapper.map_dataset(fixtures.DATASET_BARE)
        assert dataset is not None
        assert dataset.urn.endswith("raw_dump,PROD)")
        assert dataset.description is None  # blank string normalised away
        assert dataset.owners == []
        assert dataset.domain is None
        assert dataset.tags == []
        assert dataset.deprecation is None
        assert dataset.last_modified is None  # the 0 sentinel
        assert dataset.platform is None

    def test_dataset_without_urn_is_rejected(self) -> None:
        assert mapper.map_dataset({"name": "orphan"}) is None
        assert mapper.map_dataset_summary({}) is None
        assert mapper.map_dataset(None) is None

    def test_page_skips_unmappable_entries(self) -> None:
        raw = fixtures.search_response(
            fixtures.DATASET_COMPLETE, {"urn": None}, total=9
        )
        start, count, total, datasets = mapper.map_dataset_page(
            raw["searchAcrossEntities"]
        )
        assert (start, total) == (0, 9)
        assert count == 2  # what DataHub reported
        assert len(datasets) == 1  # what was actually mappable


class TestLineage:
    def test_maps_nodes_and_skips_unresolvable_ones(self) -> None:
        lineage = mapper.map_lineage(
            fixtures.LINEAGE_DOWNSTREAM["searchAcrossLineage"],
            urn="urn:li:dataset:(urn:li:dataPlatform:hive,fct_users,PROD)",
            direction=LineageDirection.DOWNSTREAM,
        )
        assert lineage.total == 2
        assert len(lineage.nodes) == 1  # the URN-less entry was dropped

        node = lineage.nodes[0]
        assert node.name == "dim_users"
        assert node.degree == 1
        assert node.deprecated is True

    def test_no_lineage_is_an_empty_graph_not_an_error(self) -> None:
        lineage = mapper.map_lineage(
            None, urn="urn:li:x", direction=LineageDirection.UPSTREAM
        )
        assert lineage.nodes == []
        assert lineage.total == 0


class TestDomains:
    def test_maps_domain_with_entity_count(self) -> None:
        _, _, total, domains = mapper.map_domain_page(
            fixtures.DOMAINS_RESPONSE["listDomains"]
        )
        assert total == 1
        assert domains[0].name == "Analytics"
        assert domains[0].entity_count == 42
        assert domains[0].description is None


class TestStatistics:
    def test_profiles_are_sorted_newest_first(self) -> None:
        stats = mapper.map_statistics(
            urn="urn:li:dataset:x",
            profiles_raw=fixtures.PROFILES_RESPONSE["dataset"]["datasetProfiles"],
            usage_raw=fixtures.USAGE_RESPONSE["dataset"]["usageStats"],
            time_range=TimeRange.MONTH,
        )
        assert stats.latest_profile is not None
        assert stats.latest_profile.row_count == 1000
        assert [p.row_count for p in stats.profiles] == [1000, 900]

        assert stats.usage is not None
        assert stats.usage.total_queries == 128
        assert stats.usage.unique_users == 4
        assert stats.usage.top_users[0].query_count == 90

    def test_absent_statistics_are_not_an_error(self) -> None:
        stats = mapper.map_statistics(
            urn="urn:li:dataset:x",
            profiles_raw=None,
            usage_raw=None,
            time_range=TimeRange.MONTH,
            usage_unavailable_reason="usage source not configured",
        )
        assert stats.profiles == []
        assert stats.latest_profile is None
        assert stats.usage is None
        assert stats.usage_unavailable_reason == "usage source not configured"
