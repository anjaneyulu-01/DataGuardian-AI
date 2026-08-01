"""DataHub integration.

Layering, outermost to innermost:

    service.py    Public interface — what the API and the agent call
    mapper.py     Raw GraphQL dicts -> Pydantic models
    queries.py    GraphQL documents
    graphql.py    GraphQL envelope handling and error translation
    client.py     HTTP transport, auth, timeouts, retries
    models.py     The typed contract
    exceptions.py Typed failures

Each layer depends only on the ones below it. Import from this package rather
than reaching into submodules, so internal restructuring stays internal.
"""

from app.integrations.datahub.client import DataHubClient
from app.integrations.datahub.exceptions import (
    DataHubAuthenticationError,
    DataHubConnectionError,
    DataHubEntityNotFoundError,
    DataHubError,
    DataHubQueryError,
    DataHubResponseError,
    DataHubTimeoutError,
)
from app.integrations.datahub.graphql import GraphQLClient
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
    Page,
    SchemaField,
    Tag,
    TimeRange,
    UsageStatistics,
    UsageUser,
)
from app.integrations.datahub.service import DataHubService

__all__ = [
    "DataHubAuthenticationError",
    "DataHubClient",
    "DataHubConnectionError",
    "DataHubEntityNotFoundError",
    "DataHubError",
    "DataHubHealth",
    "DataHubQueryError",
    "DataHubResponseError",
    "DataHubService",
    "DataHubTimeoutError",
    "DataPlatform",
    "Dataset",
    "DatasetProfile",
    "DatasetSchema",
    "DatasetStatistics",
    "DatasetSummary",
    "Deprecation",
    "Domain",
    "FieldStatistics",
    "GlossaryTerm",
    "GraphQLClient",
    "InstitutionalMemoryLink",
    "Lineage",
    "LineageDirection",
    "LineageNode",
    "Owner",
    "OwnerKind",
    "Page",
    "SchemaField",
    "Tag",
    "TimeRange",
    "UsageStatistics",
    "UsageUser",
]
