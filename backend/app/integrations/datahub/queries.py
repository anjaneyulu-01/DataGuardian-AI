"""GraphQL documents for the DataHub API.

Queries live here rather than inline in `service.py` so they can be reviewed,
diffed, and version-checked as a unit — they are the part of this integration
most likely to break when DataHub is upgraded.

Shared field selections are defined once as fragments and composed into
documents by `_document`, so adding a field to `datasetSummaryFields` updates
every query that lists datasets.

--------------------------------------------------------------------------
COMPATIBILITY
--------------------------------------------------------------------------
Written against the DataHub GraphQL schema as documented for the 0.13.x /
0.14.x line. DataHub evolves its schema between releases, and a query asking
for a field the running instance does not expose fails the *whole* query with
a GraphQL error rather than returning a partial result.

TODO(datahub): Validate every document below against the local DataHub
instance once it is running. The fastest check is to paste each query into
GraphiQL at http://localhost:9002/api/graphiql and confirm it resolves. Each
query carries its own TODO noting the fields most at risk.
"""

# ---------------------------------------------------------------------------
# Fragments — shared field selections
# ---------------------------------------------------------------------------

# `Owner.owner` is a union of CorpUser and CorpGroup, so both branches are
# selected and `__typename` tells the mapper which one came back.
#
# TODO(datahub): `Owner.type` is the legacy ownership enum (DATAOWNER,
# PRODUCER, …) and `Owner.ownershipType` is the newer custom-ownership entity.
# Both are selected for compatibility; drop `type` once the local instance is
# confirmed to populate `ownershipType`.
FRAGMENT_OWNER = """
fragment ownerFields on Owner {
  type
  ownershipType {
    urn
    info { name description }
  }
  owner {
    __typename
    ... on CorpUser {
      urn
      username
      properties { displayName email title active }
      editableProperties { displayName email }
    }
    ... on CorpGroup {
      urn
      name
      properties { displayName email description }
    }
  }
}
"""

FRAGMENT_TAG = """
fragment tagFields on GlobalTags {
  tags {
    tag {
      urn
      name
      properties { name description colorHex }
    }
  }
}
"""

FRAGMENT_DOMAIN = """
fragment domainFields on DomainAssociation {
  domain {
    urn
    id
    properties { name description }
  }
}
"""

# The field set every dataset listing returns. Detail queries spread this and
# add the expensive parts (schema, glossary terms, custom properties) on top.
FRAGMENT_DATASET_SUMMARY = """
fragment datasetSummaryFields on Dataset {
  urn
  type
  name
  platform {
    urn
    name
    properties { displayName type }
  }
  subTypes { typeNames }
  properties {
    name
    qualifiedName
    description
    externalUrl
    lastModified { time }
  }
  editableProperties { description }
  ownership { owners { ...ownerFields } }
  domain { ...domainFields }
  tags { ...tagFields }
  deprecation { deprecated note decommissionTime }
  lastIngested
}
"""

# Lineage results are deliberately shallow: a lineage graph can fan out to
# hundreds of nodes, and pulling ownership for each would be very expensive.
# Callers that need detail re-fetch the specific URN.
FRAGMENT_LINEAGE_ENTITY = """
fragment lineageEntityFields on Entity {
  urn
  type
  ... on Dataset {
    name
    platform { urn name properties { displayName } }
    properties { name qualifiedName description }
    deprecation { deprecated }
  }
}
"""


def _document(body: str, *fragments: str) -> str:
    """Join a query with the fragments it references.

    GraphQL requires every referenced fragment to be present in the same
    document; composing here keeps that wiring in one place.
    """
    return "\n".join([body.strip(), *(f.strip() for f in fragments)])


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

# TODO(datahub): `searchAcrossEntities` is the modern entry point. Very old
# instances only expose `search(input: SearchInput!)` — swap if GraphiQL
# rejects this.
LIST_DATASETS = _document(
    """
query listDatasets($query: String!, $start: Int!, $count: Int!) {
  searchAcrossEntities(
    input: { types: [DATASET], query: $query, start: $start, count: $count }
  ) {
    start
    count
    total
    searchResults {
      entity { ...datasetSummaryFields }
    }
  }
}
""",
    FRAGMENT_DATASET_SUMMARY,
    FRAGMENT_OWNER,
    FRAGMENT_DOMAIN,
    FRAGMENT_TAG,
)

# TODO(datahub): `institutionalMemory` and `editableSchemaMetadata` are present
# in 0.13+ but are the first things to disappear on trimmed-down builds.
GET_DATASET = _document(
    """
query getDataset($urn: String!) {
  dataset(urn: $urn) {
    ...datasetSummaryFields
    properties {
      customProperties { key value }
      created { time }
    }
    glossaryTerms {
      terms { term { urn name properties { name description } } }
    }
    schemaMetadata {
      name
      primaryKeys
      fields {
        fieldPath
        label
        description
        nullable
        isPartOfKey
        type
        nativeDataType
      }
    }
    institutionalMemory {
      elements { url description }
    }
  }
}
""",
    FRAGMENT_DATASET_SUMMARY,
    FRAGMENT_OWNER,
    FRAGMENT_DOMAIN,
    FRAGMENT_TAG,
)

GET_DATASET_SCHEMA = _document(
    """
query getDatasetSchema($urn: String!) {
  dataset(urn: $urn) {
    urn
    schemaMetadata {
      name
      primaryKeys
      fields {
        fieldPath
        label
        description
        nullable
        isPartOfKey
        type
        nativeDataType
      }
    }
  }
}
"""
)

# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------

GET_DATASET_OWNERS = _document(
    """
query getDatasetOwners($urn: String!) {
  dataset(urn: $urn) {
    urn
    ownership { owners { ...ownerFields } }
  }
}
""",
    FRAGMENT_OWNER,
)

# Distinct owners across the catalogue, via search facet aggregation. Far
# cheaper than paging every dataset and de-duplicating client-side.
#
# TODO(datahub): `aggregateAcrossEntities` requires roughly DataHub 0.10+. If
# the local instance rejects it, fall back to reading the `owners` facet from
# a `searchAcrossEntities` response, which exposes the same aggregation.
AGGREGATE_OWNERS = _document(
    """
query aggregateOwners($query: String!) {
  aggregateAcrossEntities(
    input: { types: [DATASET], query: $query, facets: ["owners"] }
  ) {
    facets {
      field
      displayName
      aggregations {
        value
        count
        entity {
          urn
          type
          ... on CorpUser {
            username
            properties { displayName email title active }
            editableProperties { displayName email }
          }
          ... on CorpGroup {
            name
            properties { displayName email description }
          }
        }
      }
    }
  }
}
"""
)

# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

# TODO(datahub): `ListDomainsInput` gained a `query` field in later releases;
# it is omitted here so the document works on older instances too. The nested
# `entities(input: {start: 0, count: 0})` asks for the total only — confirm the
# local instance accepts count: 0, and use count: 1 if it validates against it.
LIST_DOMAINS = _document(
    """
query listDomains($start: Int!, $count: Int!) {
  listDomains(input: { start: $start, count: $count }) {
    start
    count
    total
    domains {
      urn
      id
      properties { name description }
      ownership { owners { ...ownerFields } }
      entities(input: { start: 0, count: 0 }) { total }
    }
  }
}
""",
    FRAGMENT_OWNER,
)

GET_DOMAIN = _document(
    """
query getDomain($urn: String!) {
  domain(urn: $urn) {
    urn
    id
    properties { name description }
    ownership { owners { ...ownerFields } }
    entities(input: { start: 0, count: 0 }) { total }
  }
}
""",
    FRAGMENT_OWNER,
)

# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

LIST_TAGS = _document(
    """
query listTags($query: String!, $start: Int!, $count: Int!) {
  searchAcrossEntities(
    input: { types: [TAG], query: $query, start: $start, count: $count }
  ) {
    start
    count
    total
    searchResults {
      entity {
        urn
        type
        ... on Tag {
          name
          properties { name description colorHex }
        }
      }
    }
  }
}
"""
)

# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------

# `degree` is hop distance from the requested URN: 1 = direct neighbour. The
# agent uses it to judge blast radius.
#
# TODO(datahub): `searchAcrossLineage` supports a `degree` filter for
# multi-hop traversal on newer instances. Confirm the default depth on the
# local instance before relying on hop counts beyond 1.
GET_LINEAGE = _document(
    """
query getLineage(
  $urn: String!
  $direction: LineageDirection!
  $start: Int!
  $count: Int!
) {
  searchAcrossLineage(
    input: {
      urn: $urn
      direction: $direction
      query: "*"
      start: $start
      count: $count
    }
  ) {
    start
    count
    total
    searchResults {
      degree
      entity { ...lineageEntityFields }
    }
  }
}
""",
    FRAGMENT_LINEAGE_ENTITY,
)

# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

# Profiles and usage are two separate documents on purpose. They come from
# different ingestion sources and are independently optional: asking for both
# in one query means a missing usage source also costs us the profile data.
#
# TODO(datahub): `datasetProfiles` is populated only when profiling is enabled
# on the ingestion recipe. Expect an empty list on a fresh quickstart.
GET_DATASET_PROFILES = _document(
    """
query getDatasetProfiles($urn: String!, $limit: Int!) {
  dataset(urn: $urn) {
    urn
    datasetProfiles(limit: $limit) {
      timestampMillis
      rowCount
      columnCount
      sizeInBytes
      fieldProfiles {
        fieldPath
        uniqueCount
        uniqueProportion
        nullCount
        nullProportion
        min
        max
        mean
        median
        stdev
      }
    }
  }
}
"""
)

# TODO(datahub): `usageStats` requires a usage-ingestion source. It is absent
# on most quickstart instances, which is why the service treats a failure here
# as non-fatal and returns profiles without usage.
GET_DATASET_USAGE = _document(
    """
query getDatasetUsage($urn: String!, $range: TimeRange!) {
  dataset(urn: $urn) {
    urn
    usageStats(range: $range) {
      buckets {
        bucket
        duration
        metrics { totalSqlQueries uniqueUserCount }
      }
      aggregations {
        uniqueUserCount
        totalSqlQueries
        fields { fieldName count }
        users { count user { urn username } }
      }
    }
  }
}
"""
)

# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

# Generic entry point. `$types: [EntityType!]` left null searches everything.
SEARCH_ENTITIES = _document(
    """
query searchEntities(
  $types: [EntityType!]
  $query: String!
  $start: Int!
  $count: Int!
) {
  searchAcrossEntities(
    input: { types: $types, query: $query, start: $start, count: $count }
  ) {
    start
    count
    total
    searchResults {
      entity {
        urn
        type
        ... on Dataset { ...datasetSummaryFields }
      }
    }
  }
}
""",
    FRAGMENT_DATASET_SUMMARY,
    FRAGMENT_OWNER,
    FRAGMENT_DOMAIN,
    FRAGMENT_TAG,
)
