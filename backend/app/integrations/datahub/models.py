"""Pydantic models for DataHub metadata.

These are the integration's public contract. Everything above this layer —
the API routers today, the governance rule engine and the agent tomorrow —
depends on these models and never on raw GraphQL dictionaries. That boundary
is what lets DataHub's schema change without rippling through the codebase:
only `mapper.py` needs updating.

Design rules:

* **Optional by default.** DataHub metadata is sparse — a dataset with no
  owner, no description, and no domain is exactly the case this project
  exists to detect. Models must represent that state rather than reject it.
* **snake_case fields.** GraphQL is camelCase; translation happens in the
  mapper so Python code reads naturally.
* **No governance judgement here.** These models describe what DataHub holds.
  Deciding that a missing owner is a *violation* is the rule engine's job.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field


class _Base(BaseModel):
    """Shared configuration for every model in this module."""

    model_config = ConfigDict(frozen=True, extra="ignore")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OwnerKind(StrEnum):
    """Which kind of principal owns an asset."""

    USER = "USER"
    GROUP = "GROUP"
    UNKNOWN = "UNKNOWN"


class LineageDirection(StrEnum):
    """Traversal direction, matching DataHub's `LineageDirection` enum."""

    UPSTREAM = "UPSTREAM"
    DOWNSTREAM = "DOWNSTREAM"


class TimeRange(StrEnum):
    """Window for usage statistics, matching DataHub's `TimeRange` enum."""

    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    QUARTER = "QUARTER"
    YEAR = "YEAR"


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


class Owner(_Base):
    """A user or group responsible for an asset."""

    urn: str
    kind: OwnerKind = OwnerKind.UNKNOWN
    # CorpUser.username or CorpGroup.name — the stable machine identifier.
    name: str | None = None
    display_name: str | None = None
    email: str | None = None
    title: str | None = None
    active: bool | None = None
    # "TECHNICAL_OWNER", "DATAOWNER", … Free-form because DataHub allows
    # custom ownership types.
    ownership_type: str | None = None
    # How many assets this owner owns. Only set by aggregation queries.
    asset_count: int | None = None


class Tag(_Base):
    """A DataHub tag. Tags carrying PII semantics drive governance rules."""

    urn: str
    name: str
    description: str | None = None
    color_hex: str | None = None


class GlossaryTerm(_Base):
    """A business glossary term attached to an asset."""

    urn: str
    name: str
    description: str | None = None


class Domain(_Base):
    """A DataHub domain — the business grouping an asset belongs to."""

    urn: str
    id: str | None = None
    name: str | None = None
    description: str | None = None
    owners: list[Owner] = Field(default_factory=list)
    # Number of assets in the domain; None when not requested.
    entity_count: int | None = None


class DataPlatform(_Base):
    """The system a dataset physically lives in (Snowflake, Hive, …)."""

    urn: str
    name: str
    display_name: str | None = None


class Deprecation(_Base):
    """Deprecation status. A deprecated asset with live downstreams is a
    governance finding the agent will care about."""

    deprecated: bool = False
    note: str | None = None
    decommission_time: datetime | None = None


class SchemaField(_Base):
    """One column in a dataset's schema."""

    field_path: str
    label: str | None = None
    description: str | None = None
    # DataHub's normalised type (STRING, NUMBER, …).
    type: str | None = None
    # The platform's own type name (VARCHAR(255), …).
    native_data_type: str | None = None
    nullable: bool | None = None
    is_part_of_key: bool = False


class DatasetSchema(_Base):
    """A dataset's column layout."""

    name: str | None = None
    primary_keys: list[str] = Field(default_factory=list)
    fields: list[SchemaField] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def field_count(self) -> int:
        return len(self.fields)


class InstitutionalMemoryLink(_Base):
    """A documentation link attached to an asset (wiki, runbook, dashboard)."""

    url: str
    description: str | None = None


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------


class DatasetSummary(_Base):
    """A dataset as it appears in a listing.

    Carries everything the governance rules need to flag an asset without a
    second round-trip: ownership, description, domain, tags, deprecation.
    """

    urn: str
    name: str | None = None
    qualified_name: str | None = None
    platform: DataPlatform | None = None
    # DataHub keeps a technical description and a UI-editable one. This is the
    # effective value: editable wins, matching what a steward sees.
    description: str | None = None
    sub_types: list[str] = Field(default_factory=list)
    owners: list[Owner] = Field(default_factory=list)
    domain: Domain | None = None
    tags: list[Tag] = Field(default_factory=list)
    deprecation: Deprecation | None = None
    external_url: str | None = None
    last_modified: datetime | None = None
    last_ingested: datetime | None = None


class Dataset(DatasetSummary):
    """A dataset with its full metadata, from the detail query."""

    glossary_terms: list[GlossaryTerm] = Field(default_factory=list)
    schema_metadata: DatasetSchema | None = None
    custom_properties: dict[str, str] = Field(default_factory=dict)
    institutional_memory: list[InstitutionalMemoryLink] = Field(default_factory=list)
    created: datetime | None = None


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------


class LineageNode(_Base):
    """One asset reached while traversing lineage."""

    urn: str
    entity_type: str
    name: str | None = None
    qualified_name: str | None = None
    description: str | None = None
    platform: DataPlatform | None = None
    # Hops from the origin URN; 1 is a direct neighbour.
    degree: int | None = None
    deprecated: bool = False


class Lineage(_Base):
    """The lineage of one asset in a single direction.

    Upstream and downstream are fetched separately because DataHub traverses
    them independently, and most callers only need one side.
    """

    urn: str
    direction: LineageDirection
    total: int = 0
    nodes: list[LineageNode] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class FieldStatistics(_Base):
    """Profiled statistics for a single column."""

    field_path: str
    unique_count: int | None = None
    unique_proportion: float | None = None
    null_count: int | None = None
    null_proportion: float | None = None
    min: str | None = None
    max: str | None = None
    mean: str | None = None
    median: str | None = None
    stdev: str | None = None


class DatasetProfile(_Base):
    """One profiling snapshot of a dataset."""

    timestamp: datetime | None = None
    row_count: int | None = None
    column_count: int | None = None
    size_in_bytes: int | None = None
    fields: list[FieldStatistics] = Field(default_factory=list)


class UsageUser(_Base):
    """A principal that queried a dataset, with how often.

    Deliberately not an `Owner`: the count here is a query count, and reusing
    `Owner.asset_count` for it would conflate two different measures.
    """

    urn: str
    username: str | None = None
    query_count: int | None = None


class UsageStatistics(_Base):
    """Query-usage aggregates over a time range."""

    time_range: TimeRange
    total_queries: int | None = None
    unique_users: int | None = None
    top_users: list[UsageUser] = Field(default_factory=list)


class DatasetStatistics(_Base):
    """Everything quantitative known about one dataset.

    `profiles` and `usage` are independently optional: a fresh DataHub without
    profiling or usage ingestion returns neither, which is a legitimate state
    and not an error.
    """

    urn: str
    latest_profile: DatasetProfile | None = None
    profiles: list[DatasetProfile] = Field(default_factory=list)
    usage: UsageStatistics | None = None
    # Set when usage was requested but the instance could not serve it, so
    # callers can tell "no usage data" from "usage not available here".
    usage_unavailable_reason: str | None = None


# ---------------------------------------------------------------------------
# Pagination and health
# ---------------------------------------------------------------------------


class Page[T](_Base):
    """A slice of a result set, mirroring DataHub's search pagination."""

    start: int = 0
    count: int = 0
    total: int = 0
    results: list[T] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_more(self) -> bool:
        """Whether another page exists. Serialised, so clients can loop
        without recomputing the arithmetic."""
        return self.start + len(self.results) < self.total


class DataHubHealth(_Base):
    """Result of the DataHub connectivity probe.

    Reported honestly: when DataHub is unreachable this returns
    `reachable=False` with the reason, rather than raising. A monitoring
    endpoint that 502s tells you less than one that explains itself.
    """

    reachable: bool
    gms_url: str
    authenticated: bool
    version: str | None = None
    latency_ms: float | None = None
    error: str | None = None
