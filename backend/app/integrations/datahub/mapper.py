"""Translation from raw GraphQL responses into the models in `models.py`.

This module is the blast door. DataHub's GraphQL payloads are deeply nested,
inconsistently populated, and change between releases; everything above this
layer sees only clean, typed models. When DataHub changes shape, this file is
the only one that should need editing.

Every function here follows the same two rules:

* **Never raise on missing data.** A dataset with no ownership aspect returns
  an empty owner list, not a KeyError. Sparse metadata is the normal case —
  it is the thing DataGuardian exists to find — so the mapper must survive it.
  Genuinely absent *entities* are handled in `service.py`, which raises
  `DataHubEntityNotFoundError`; that is a different condition from an entity
  with missing aspects.
* **Pure functions, no I/O.** Everything is a plain dict-in / model-out
  transformation, which makes this the cheapest layer in the stack to test.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from app.integrations.datahub.models import (
    DataHubHealth,
    DataPlatform,
    Dataset,
    DatasetProfile,
    DatasetSchema,
    DatasetStatistics,
    DatasetSummary,
    Deprecation,
    Domain,
    FieldStatistics,
    GlossaryTerm,
    InstitutionalMemoryLink,
    Lineage,
    LineageDirection,
    LineageNode,
    Owner,
    OwnerKind,
    SchemaField,
    Tag,
    TimeRange,
    UsageStatistics,
    UsageUser,
)

logger = logging.getLogger(__name__)

# DataHub's GraphQL __typename values for the CorpUser / CorpGroup union.
_OWNER_KIND_BY_TYPENAME = {
    "CorpUser": OwnerKind.USER,
    "CorpGroup": OwnerKind.GROUP,
}


# ---------------------------------------------------------------------------
# Safe traversal helpers
# ---------------------------------------------------------------------------


def as_dict(value: Any) -> dict[str, Any]:
    """Coerce a value to a dict. GraphQL nulls become empty objects.

    Public because `service.py` needs the same null-safety when it reaches
    into a response before delegating to a mapper function.
    """
    return value if isinstance(value, dict) else {}


# Internal alias — this module uses the short name heavily.
_obj = as_dict


def _seq(value: Any) -> list[Any]:
    """Coerce a value to a list. GraphQL nulls become empty lists."""
    return value if isinstance(value, list) else []


def _dig(source: Any, *keys: str) -> Any:
    """Walk a nested path, returning None if any hop is missing or null.

    ``_dig(raw, "properties", "lastModified", "time")`` replaces three nested
    ``.get()`` calls and cannot raise.
    """
    current: Any = source
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _text(value: Any) -> str | None:
    """Normalise a string field: strip it, and treat blank as absent.

    DataHub commonly stores an empty-string description, which is
    indistinguishable from no description for governance purposes.
    """
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _int(value: Any) -> int | None:
    """Coerce a numeric field, tolerating the strings DataHub sometimes sends."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _timestamp(value: Any) -> datetime | None:
    """Convert DataHub's epoch-milliseconds timestamps to aware datetimes.

    DataHub returns 0 for "never", which would otherwise map to 1970 and make
    every unmodified asset look ancient to the staleness rules.
    """
    millis = _int(value)
    if millis is None or millis <= 0:
        return None
    try:
        return datetime.fromtimestamp(millis / 1000, tz=UTC)
    except (OverflowError, OSError, ValueError):
        logger.debug("Discarding out-of-range DataHub timestamp: %r", value)
        return None


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


def map_owner(raw: Any) -> Owner | None:
    """Map one entry of `ownership.owners`.

    Returns None when the entry has no resolvable URN, which happens for
    ownership pointing at a principal that has since been removed.
    """
    entry = _obj(raw)
    owner = _obj(entry.get("owner"))
    urn = _text(owner.get("urn"))
    if not urn:
        return None

    kind = _OWNER_KIND_BY_TYPENAME.get(str(owner.get("__typename")), OwnerKind.UNKNOWN)
    properties = _obj(owner.get("properties"))
    editable = _obj(owner.get("editableProperties"))

    # CorpUser identifies by `username`, CorpGroup by `name`.
    name = _text(owner.get("username")) or _text(owner.get("name"))

    # The UI-editable value wins, matching what a steward actually sees.
    display_name = (
        _text(editable.get("displayName"))
        or _text(properties.get("displayName"))
        or name
    )
    email = _text(editable.get("email")) or _text(properties.get("email"))

    # `ownershipType` is the modern custom entity; `type` is the legacy enum.
    ownership_type = _text(_dig(entry, "ownershipType", "info", "name")) or _text(
        entry.get("type")
    )

    return Owner(
        urn=urn,
        kind=kind,
        name=name,
        display_name=display_name,
        email=email,
        title=_text(properties.get("title")),
        active=properties.get("active")
        if isinstance(properties.get("active"), bool)
        else None,
        ownership_type=ownership_type,
    )


def map_owners(ownership_raw: Any) -> list[Owner]:
    """Map an `ownership` aspect into a de-duplicated owner list.

    DataHub allows the same principal to appear once per ownership type
    (a person can be both technical and business owner). Callers asking "does
    this asset have an owner?" want distinct principals, so the first entry
    per URN wins and its ownership type is kept.
    """
    seen: dict[str, Owner] = {}
    for entry in _seq(_dig(ownership_raw, "owners")):
        owner = map_owner(entry)
        if owner and owner.urn not in seen:
            seen[owner.urn] = owner
    return list(seen.values())


def map_tags(global_tags_raw: Any) -> list[Tag]:
    """Map a `GlobalTags` aspect."""
    tags: list[Tag] = []
    for entry in _seq(_dig(global_tags_raw, "tags")):
        tag_raw = _obj(_obj(entry).get("tag"))
        urn = _text(tag_raw.get("urn"))
        if not urn:
            continue
        properties = _obj(tag_raw.get("properties"))
        name = _text(properties.get("name")) or _text(tag_raw.get("name"))
        tags.append(
            Tag(
                urn=urn,
                # URN tail is the last resort so a tag is never nameless.
                name=name or urn.rsplit(":", 1)[-1],
                description=_text(properties.get("description")),
                color_hex=_text(properties.get("colorHex")),
            )
        )
    return tags


def map_glossary_terms(raw: Any) -> list[GlossaryTerm]:
    """Map a `glossaryTerms` aspect."""
    terms: list[GlossaryTerm] = []
    for entry in _seq(_dig(raw, "terms")):
        term_raw = _obj(_obj(entry).get("term"))
        urn = _text(term_raw.get("urn"))
        if not urn:
            continue
        properties = _obj(term_raw.get("properties"))
        terms.append(
            GlossaryTerm(
                urn=urn,
                name=_text(properties.get("name"))
                or _text(term_raw.get("name"))
                or urn.rsplit(":", 1)[-1],
                description=_text(properties.get("description")),
            )
        )
    return terms


def map_platform(raw: Any) -> DataPlatform | None:
    """Map a `platform` object."""
    platform = _obj(raw)
    urn = _text(platform.get("urn"))
    name = _text(platform.get("name"))
    if not urn and not name:
        return None
    return DataPlatform(
        urn=urn or name or "",
        name=name or (urn or "").rsplit(":", 1)[-1],
        display_name=_text(_dig(platform, "properties", "displayName")),
    )


def map_domain_association(raw: Any) -> Domain | None:
    """Map a dataset's `domain` field (a `DomainAssociation` wrapper)."""
    return map_domain(_dig(raw, "domain"))


def map_domain(raw: Any) -> Domain | None:
    """Map a `Domain` entity."""
    domain = _obj(raw)
    urn = _text(domain.get("urn"))
    if not urn:
        return None
    properties = _obj(domain.get("properties"))
    return Domain(
        urn=urn,
        id=_text(domain.get("id")),
        name=_text(properties.get("name")),
        description=_text(properties.get("description")),
        owners=map_owners(domain.get("ownership")),
        entity_count=_int(_dig(domain, "entities", "total")),
    )


def map_deprecation(raw: Any) -> Deprecation | None:
    """Map a `deprecation` aspect. Absent means 'not deprecated'."""
    deprecation = _obj(raw)
    if not deprecation:
        return None
    return Deprecation(
        deprecated=bool(deprecation.get("deprecated")),
        note=_text(deprecation.get("note")),
        decommission_time=_timestamp(deprecation.get("decommissionTime")),
    )


def map_schema_field(raw: Any) -> SchemaField | None:
    field = _obj(raw)
    field_path = _text(field.get("fieldPath"))
    if not field_path:
        return None
    return SchemaField(
        field_path=field_path,
        label=_text(field.get("label")),
        description=_text(field.get("description")),
        type=_text(field.get("type")),
        native_data_type=_text(field.get("nativeDataType")),
        nullable=field.get("nullable")
        if isinstance(field.get("nullable"), bool)
        else None,
        is_part_of_key=bool(field.get("isPartOfKey")),
    )


def map_schema(raw: Any) -> DatasetSchema | None:
    """Map a `schemaMetadata` aspect."""
    schema = _obj(raw)
    if not schema:
        return None
    fields = [f for f in (map_schema_field(f) for f in _seq(schema.get("fields"))) if f]
    return DatasetSchema(
        name=_text(schema.get("name")),
        primary_keys=[k for k in _seq(schema.get("primaryKeys")) if isinstance(k, str)],
        fields=fields,
    )


def map_institutional_memory(raw: Any) -> list[InstitutionalMemoryLink]:
    links: list[InstitutionalMemoryLink] = []
    for entry in _seq(_dig(raw, "elements")):
        element = _obj(entry)
        url = _text(element.get("url"))
        if not url:
            continue
        links.append(
            InstitutionalMemoryLink(
                url=url, description=_text(element.get("description"))
            )
        )
    return links


def map_custom_properties(raw: Any) -> dict[str, str]:
    """Map `properties.customProperties` (a key/value pair list) to a dict."""
    properties: dict[str, str] = {}
    for entry in _seq(raw):
        pair = _obj(entry)
        key = _text(pair.get("key"))
        if key is not None:
            properties[key] = str(pair.get("value", ""))
    return properties


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------


def _effective_description(raw: dict[str, Any]) -> str | None:
    """Resolve the description a steward would see.

    DataHub stores an ingested technical description on `properties` and a
    UI-edited override on `editableProperties`. The override wins.
    """
    return _text(_dig(raw, "editableProperties", "description")) or _text(
        _dig(raw, "properties", "description")
    )


def _dataset_summary_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Shared field extraction for both the summary and detail mappers.

    Exists so `map_dataset` never duplicates `map_dataset_summary`'s logic.
    """
    properties = _obj(raw.get("properties"))
    return {
        "urn": _text(raw.get("urn")) or "",
        # `properties.name` is the display name; `name` is the fallback.
        "name": _text(properties.get("name")) or _text(raw.get("name")),
        "qualified_name": _text(properties.get("qualifiedName")),
        "platform": map_platform(raw.get("platform")),
        "description": _effective_description(raw),
        "sub_types": [
            t for t in _seq(_dig(raw, "subTypes", "typeNames")) if isinstance(t, str)
        ],
        "owners": map_owners(raw.get("ownership")),
        "domain": map_domain_association(raw.get("domain")),
        "tags": map_tags(raw.get("tags")),
        "deprecation": map_deprecation(raw.get("deprecation")),
        "external_url": _text(properties.get("externalUrl")),
        "last_modified": _timestamp(_dig(properties, "lastModified", "time")),
        "last_ingested": _timestamp(raw.get("lastIngested")),
    }


def map_dataset_summary(raw: Any) -> DatasetSummary | None:
    """Map a dataset from a search result. None when it has no URN."""
    dataset = _obj(raw)
    fields = _dataset_summary_fields(dataset)
    if not fields["urn"]:
        return None
    return DatasetSummary(**fields)


def map_dataset(raw: Any) -> Dataset | None:
    """Map a dataset from the detail query."""
    dataset = _obj(raw)
    fields = _dataset_summary_fields(dataset)
    if not fields["urn"]:
        return None

    properties = _obj(dataset.get("properties"))
    return Dataset(
        **fields,
        glossary_terms=map_glossary_terms(dataset.get("glossaryTerms")),
        schema_metadata=map_schema(dataset.get("schemaMetadata")),
        custom_properties=map_custom_properties(properties.get("customProperties")),
        institutional_memory=map_institutional_memory(
            dataset.get("institutionalMemory")
        ),
        created=_timestamp(_dig(properties, "created", "time")),
    )


def map_dataset_page(raw: Any) -> tuple[int, int, int, list[DatasetSummary]]:
    """Map a `searchAcrossEntities` result into pagination plus datasets.

    Returns a tuple rather than a `Page` so the service owns model
    construction and this module stays free of generics.
    """
    result = _obj(raw)
    datasets: list[DatasetSummary] = []
    for entry in _seq(result.get("searchResults")):
        dataset = map_dataset_summary(_obj(entry).get("entity"))
        if dataset:
            datasets.append(dataset)
    return (
        _int(result.get("start")) or 0,
        _int(result.get("count")) or 0,
        _int(result.get("total")) or 0,
        datasets,
    )


def map_tag_page(raw: Any) -> tuple[int, int, int, list[Tag]]:
    """Map a `searchAcrossEntities` result restricted to TAG entities."""
    result = _obj(raw)
    tags: list[Tag] = []
    for entry in _seq(result.get("searchResults")):
        entity = _obj(_obj(entry).get("entity"))
        urn = _text(entity.get("urn"))
        if not urn:
            continue
        properties = _obj(entity.get("properties"))
        tags.append(
            Tag(
                urn=urn,
                name=_text(properties.get("name"))
                or _text(entity.get("name"))
                or urn.rsplit(":", 1)[-1],
                description=_text(properties.get("description")),
                color_hex=_text(properties.get("colorHex")),
            )
        )
    return (
        _int(result.get("start")) or 0,
        _int(result.get("count")) or 0,
        _int(result.get("total")) or 0,
        tags,
    )


# ---------------------------------------------------------------------------
# Domains and owners
# ---------------------------------------------------------------------------


def map_domain_page(raw: Any) -> tuple[int, int, int, list[Domain]]:
    """Map a `listDomains` result."""
    result = _obj(raw)
    domains = [d for d in (map_domain(d) for d in _seq(result.get("domains"))) if d]
    return (
        _int(result.get("start")) or 0,
        _int(result.get("count")) or 0,
        _int(result.get("total")) or 0,
        domains,
    )


def map_owner_aggregations(raw: Any) -> list[Owner]:
    """Map an `aggregateAcrossEntities` response into distinct owners.

    Each aggregation bucket is one principal plus the number of datasets it
    owns. The `entity` sub-object may be null when the owner URN no longer
    resolves — a dangling reference, which is itself worth surfacing, so the
    owner is still returned with whatever the URN reveals.
    """
    owners: list[Owner] = []
    for facet in _seq(_dig(raw, "facets")):
        facet_obj = _obj(facet)
        if facet_obj.get("field") != "owners":
            continue

        for bucket in _seq(facet_obj.get("aggregations")):
            bucket_obj = _obj(bucket)
            entity = _obj(bucket_obj.get("entity"))
            urn = _text(entity.get("urn")) or _text(bucket_obj.get("value"))
            if not urn:
                continue

            properties = _obj(entity.get("properties"))
            editable = _obj(entity.get("editableProperties"))
            name = _text(entity.get("username")) or _text(entity.get("name"))
            kind = _OWNER_KIND_BY_TYPENAME.get(
                str(entity.get("type", "")).title().replace("_", ""),
                _owner_kind_from_urn(urn),
            )

            owners.append(
                Owner(
                    urn=urn,
                    kind=kind,
                    name=name,
                    display_name=(
                        _text(editable.get("displayName"))
                        or _text(properties.get("displayName"))
                        or name
                    ),
                    email=_text(editable.get("email"))
                    or _text(properties.get("email")),
                    title=_text(properties.get("title")),
                    active=properties.get("active")
                    if isinstance(properties.get("active"), bool)
                    else None,
                    asset_count=_int(bucket_obj.get("count")),
                )
            )
    return owners


def _owner_kind_from_urn(urn: str) -> OwnerKind:
    """Infer the principal kind from a URN when the entity did not resolve."""
    if urn.startswith("urn:li:corpuser:"):
        return OwnerKind.USER
    if urn.startswith("urn:li:corpGroup:"):
        return OwnerKind.GROUP
    return OwnerKind.UNKNOWN


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------


def map_lineage_node(raw: Any) -> LineageNode | None:
    """Map one `searchAcrossLineage` result."""
    entry = _obj(raw)
    entity = _obj(entry.get("entity"))
    urn = _text(entity.get("urn"))
    if not urn:
        return None

    properties = _obj(entity.get("properties"))
    return LineageNode(
        urn=urn,
        entity_type=_text(entity.get("type")) or "UNKNOWN",
        name=_text(properties.get("name")) or _text(entity.get("name")),
        qualified_name=_text(properties.get("qualifiedName")),
        description=_text(properties.get("description")),
        platform=map_platform(entity.get("platform")),
        degree=_int(entry.get("degree")),
        deprecated=bool(_dig(entity, "deprecation", "deprecated")),
    )


def map_lineage(raw: Any, urn: str, direction: LineageDirection) -> Lineage:
    """Map a `searchAcrossLineage` response.

    An asset with no lineage is normal, not an error: the result is a Lineage
    with zero nodes.
    """
    result = _obj(raw)
    nodes = [
        n for n in (map_lineage_node(r) for r in _seq(result.get("searchResults"))) if n
    ]
    return Lineage(
        urn=urn,
        direction=direction,
        total=_int(result.get("total")) or 0,
        nodes=nodes,
    )


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def map_field_statistics(raw: Any) -> FieldStatistics | None:
    field = _obj(raw)
    field_path = _text(field.get("fieldPath"))
    if not field_path:
        return None
    return FieldStatistics(
        field_path=field_path,
        unique_count=_int(field.get("uniqueCount")),
        unique_proportion=_float(field.get("uniqueProportion")),
        null_count=_int(field.get("nullCount")),
        null_proportion=_float(field.get("nullProportion")),
        # DataHub returns these as strings because a column's min/max is not
        # necessarily numeric.
        min=_text(field.get("min")),
        max=_text(field.get("max")),
        mean=_text(field.get("mean")),
        median=_text(field.get("median")),
        stdev=_text(field.get("stdev")),
    )


def map_profile(raw: Any) -> DatasetProfile:
    profile = _obj(raw)
    fields = [
        f
        for f in (map_field_statistics(f) for f in _seq(profile.get("fieldProfiles")))
        if f
    ]
    return DatasetProfile(
        timestamp=_timestamp(profile.get("timestampMillis")),
        row_count=_int(profile.get("rowCount")),
        column_count=_int(profile.get("columnCount")),
        size_in_bytes=_int(profile.get("sizeInBytes")),
        fields=fields,
    )


def map_profiles(raw: Any) -> list[DatasetProfile]:
    """Map `datasetProfiles`, newest first.

    DataHub does not guarantee ordering, so the sort is explicit — the
    freshness rules depend on knowing which profile is the latest.
    """
    profiles = [map_profile(p) for p in _seq(raw)]
    return sorted(
        profiles,
        key=lambda p: p.timestamp or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )


def map_usage(raw: Any, time_range: TimeRange) -> UsageStatistics | None:
    """Map a `usageStats` response."""
    usage = _obj(raw)
    if not usage:
        return None

    aggregations = _obj(usage.get("aggregations"))
    top_users: list[UsageUser] = []
    for entry in _seq(aggregations.get("users")):
        user_entry = _obj(entry)
        user = _obj(user_entry.get("user"))
        user_urn = _text(user.get("urn"))
        if not user_urn:
            continue
        top_users.append(
            UsageUser(
                urn=user_urn,
                username=_text(user.get("username")),
                query_count=_int(user_entry.get("count")),
            )
        )

    return UsageStatistics(
        time_range=time_range,
        total_queries=_int(aggregations.get("totalSqlQueries")),
        unique_users=_int(aggregations.get("uniqueUserCount")),
        top_users=top_users,
    )


def map_statistics(
    urn: str,
    profiles_raw: Any,
    usage_raw: Any,
    time_range: TimeRange,
    usage_unavailable_reason: str | None = None,
) -> DatasetStatistics:
    """Assemble profiles and usage into one statistics model."""
    profiles = map_profiles(profiles_raw)
    return DatasetStatistics(
        urn=urn,
        latest_profile=profiles[0] if profiles else None,
        profiles=profiles,
        usage=map_usage(usage_raw, time_range) if usage_raw else None,
        usage_unavailable_reason=usage_unavailable_reason,
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def map_health(
    gms_url: str,
    authenticated: bool,
    reachable: bool,
    config_raw: Any = None,
    latency_ms: float | None = None,
    error: str | None = None,
) -> DataHubHealth:
    """Build the health model from the GMS `/config` response.

    TODO(datahub): `/config` returns a `versions` object whose exact shape has
    changed across releases. The lookup below covers the known layouts and
    degrades to `version=None` rather than failing the health check.
    """
    config = _obj(config_raw)
    versions = _obj(config.get("versions"))
    acryl = _obj(versions.get("acryldata/datahub"))
    version = _text(acryl.get("version")) or _text(config.get("datahub_version"))

    return DataHubHealth(
        reachable=reachable,
        gms_url=gms_url,
        authenticated=authenticated,
        version=version,
        latency_ms=latency_ms,
        error=error,
    )
