"""GraphQL response doubles used by the test suite.

These are NOT sample data and are never served by the application. They are
hand-written to reproduce the response shapes DataHub actually returns,
including the awkward ones — null aspects, blank descriptions, duplicate
owners, unresolvable URNs — so the mapper is proven against sparse metadata
rather than only the happy path.

TODO(datahub): Once the local DataHub instance is running, capture a real
response for each operation and replace these by hand, keeping the degenerate
cases below. Recorded fixtures catch schema drift that hand-written ones
cannot.
"""

from typing import Any

# A fully populated dataset: every aspect present.
DATASET_COMPLETE: dict[str, Any] = {
    "urn": "urn:li:dataset:(urn:li:dataPlatform:hive,fct_users,PROD)",
    "type": "DATASET",
    "name": "fct_users",
    "platform": {
        "urn": "urn:li:dataPlatform:hive",
        "name": "hive",
        "properties": {"displayName": "Hive", "type": "FILE_SYSTEM"},
    },
    "subTypes": {"typeNames": ["Table"]},
    "properties": {
        "name": "fct_users",
        "qualifiedName": "prod.analytics.fct_users",
        "description": "  User fact table.  ",
        "externalUrl": "https://example.invalid/fct_users",
        "lastModified": {"time": 1735689600000},
        "created": {"time": 1704067200000},
        "customProperties": [
            {"key": "retention_days", "value": "90"},
            {"key": "pii", "value": "true"},
        ],
    },
    "editableProperties": {"description": "Curated user fact table."},
    "ownership": {
        "owners": [
            {
                "type": "DATAOWNER",
                "ownershipType": {
                    "urn": "urn:li:ownershipType:technical",
                    "info": {"name": "Technical Owner", "description": None},
                },
                "owner": {
                    "__typename": "CorpUser",
                    "urn": "urn:li:corpuser:aditi",
                    "username": "aditi",
                    "properties": {
                        "displayName": "Aditi R",
                        "email": "aditi@example.invalid",
                        "title": "Data Engineer",
                        "active": True,
                    },
                    "editableProperties": {"displayName": "Aditi (Data Eng)"},
                },
            },
            # Same principal, second ownership type — must be de-duplicated.
            {
                "type": "BUSINESS_OWNER",
                "ownershipType": None,
                "owner": {
                    "__typename": "CorpUser",
                    "urn": "urn:li:corpuser:aditi",
                    "username": "aditi",
                    "properties": {"displayName": "Aditi R"},
                },
            },
            {
                "type": None,
                "ownershipType": None,
                "owner": {
                    "__typename": "CorpGroup",
                    "urn": "urn:li:corpGroup:platform",
                    "name": "platform",
                    "properties": {"displayName": "Platform Team"},
                },
            },
        ]
    },
    "domain": {
        "domain": {
            "urn": "urn:li:domain:analytics",
            "id": "analytics",
            "properties": {"name": "Analytics", "description": "Analytics assets"},
        }
    },
    "tags": {
        "tags": [
            {
                "tag": {
                    "urn": "urn:li:tag:PII",
                    "name": "PII",
                    "properties": {
                        "name": "PII",
                        "description": "Contains personal data",
                        "colorHex": "#ff0000",
                    },
                }
            }
        ]
    },
    "deprecation": {
        "deprecated": False,
        "note": None,
        "decommissionTime": None,
    },
    "lastIngested": 1735776000000,
    "glossaryTerms": {
        "terms": [
            {
                "term": {
                    "urn": "urn:li:glossaryTerm:CustomerData",
                    "name": "CustomerData",
                    "properties": {"name": "Customer Data", "description": None},
                }
            }
        ]
    },
    "schemaMetadata": {
        "name": "fct_users",
        "primaryKeys": ["user_id"],
        "fields": [
            {
                "fieldPath": "user_id",
                "label": None,
                "description": "Primary key",
                "nullable": False,
                "isPartOfKey": True,
                "type": "NUMBER",
                "nativeDataType": "BIGINT",
            },
            {
                "fieldPath": "email",
                "label": None,
                "description": None,
                "nullable": True,
                "isPartOfKey": False,
                "type": "STRING",
                "nativeDataType": "VARCHAR(255)",
            },
        ],
    },
    "institutionalMemory": {
        "elements": [
            {"url": "https://wiki.example.invalid/fct_users", "description": "Runbook"}
        ]
    },
}

# The governance-relevant degenerate case: an asset with no owner, no
# description, no domain, and no tags. Exactly what DataGuardian exists to
# find, so the mapper must handle it without raising.
DATASET_BARE: dict[str, Any] = {
    "urn": "urn:li:dataset:(urn:li:dataPlatform:s3,raw_dump,PROD)",
    "type": "DATASET",
    "name": "raw_dump",
    "platform": None,
    "subTypes": None,
    "properties": {
        "name": None,
        "qualifiedName": None,
        # Blank, not absent — must normalise to None.
        "description": "   ",
        "externalUrl": None,
        # DataHub's "never" sentinel; must not become 1970.
        "lastModified": {"time": 0},
    },
    "editableProperties": None,
    "ownership": None,
    "domain": None,
    "tags": None,
    "deprecation": None,
    "lastIngested": None,
}


def search_response(*datasets: dict[str, Any], total: int | None = None) -> dict:
    """Wrap datasets in a `searchAcrossEntities` envelope."""
    return {
        "searchAcrossEntities": {
            "start": 0,
            "count": len(datasets),
            "total": len(datasets) if total is None else total,
            "searchResults": [{"entity": d} for d in datasets],
        }
    }


LINEAGE_DOWNSTREAM: dict[str, Any] = {
    "searchAcrossLineage": {
        "start": 0,
        "count": 2,
        "total": 2,
        "searchResults": [
            {
                "degree": 1,
                "entity": {
                    "urn": "urn:li:dataset:(urn:li:dataPlatform:hive,dim_users,PROD)",
                    "type": "DATASET",
                    "name": "dim_users",
                    "platform": {
                        "urn": "urn:li:dataPlatform:hive",
                        "name": "hive",
                        "properties": {"displayName": "Hive"},
                    },
                    "properties": {
                        "name": "dim_users",
                        "qualifiedName": "prod.analytics.dim_users",
                        "description": "User dimension",
                    },
                    "deprecation": {"deprecated": True},
                },
            },
            # Degenerate: no URN, must be skipped rather than crash.
            {"degree": 2, "entity": {"urn": None, "type": "DATASET"}},
        ],
    }
}

DOMAINS_RESPONSE: dict[str, Any] = {
    "listDomains": {
        "start": 0,
        "count": 1,
        "total": 1,
        "domains": [
            {
                "urn": "urn:li:domain:analytics",
                "id": "analytics",
                "properties": {"name": "Analytics", "description": None},
                "ownership": None,
                "entities": {"total": 42},
            }
        ],
    }
}

OWNER_AGGREGATIONS: dict[str, Any] = {
    "aggregateAcrossEntities": {
        "facets": [
            {"field": "platform", "displayName": "Platform", "aggregations": []},
            {
                "field": "owners",
                "displayName": "Owners",
                "aggregations": [
                    {
                        "value": "urn:li:corpuser:aditi",
                        "count": 12,
                        "entity": {
                            "urn": "urn:li:corpuser:aditi",
                            "type": "CORP_USER",
                            "username": "aditi",
                            "properties": {
                                "displayName": "Aditi R",
                                "email": "aditi@example.invalid",
                                "active": True,
                            },
                            "editableProperties": None,
                        },
                    },
                    # Dangling reference: the owner URN no longer resolves.
                    # Still returned — a broken owner reference is itself a
                    # governance problem.
                    {
                        "value": "urn:li:corpuser:departed",
                        "count": 3,
                        "entity": None,
                    },
                ],
            },
        ]
    }
}

PROFILES_RESPONSE: dict[str, Any] = {
    "dataset": {
        "urn": "urn:li:dataset:(urn:li:dataPlatform:hive,fct_users,PROD)",
        "datasetProfiles": [
            # Deliberately out of order — the mapper must sort newest first.
            {
                "timestampMillis": 1735603200000,
                "rowCount": 900,
                "columnCount": 2,
                "sizeInBytes": 1024,
                "fieldProfiles": [],
            },
            {
                "timestampMillis": 1735689600000,
                "rowCount": 1000,
                "columnCount": 2,
                "sizeInBytes": 2048,
                "fieldProfiles": [
                    {
                        "fieldPath": "email",
                        "uniqueCount": 990,
                        "uniqueProportion": 0.99,
                        "nullCount": 10,
                        "nullProportion": 0.01,
                        "min": None,
                        "max": None,
                        "mean": None,
                        "median": None,
                        "stdev": None,
                    }
                ],
            },
        ],
    }
}

USAGE_RESPONSE: dict[str, Any] = {
    "dataset": {
        "urn": "urn:li:dataset:(urn:li:dataPlatform:hive,fct_users,PROD)",
        "usageStats": {
            "buckets": [],
            "aggregations": {
                "uniqueUserCount": 4,
                "totalSqlQueries": 128,
                "fields": [{"fieldName": "email", "count": 40}],
                "users": [
                    {
                        "count": 90,
                        "user": {"urn": "urn:li:corpuser:aditi", "username": "aditi"},
                    }
                ],
            },
        },
    }
}
