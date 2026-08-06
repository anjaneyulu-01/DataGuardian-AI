"""Seed DataHub with a demo catalogue for DataGuardian.

Why this exists rather than `datahub docker ingest-sample-data`: that command
is broken in the current CLI (v1.6.x raises "Did not find a registered class
for c" from its bundled source), and its generic sample data does not
exercise the governance rules this product detects.

The catalogue below is purpose-built: each asset is missing something
specific, so every rule in `app/agents/risk_engine.py` fires at least once and
the demo shows real findings rather than an empty scan.

    pip install acryl-datahub
    python datahub/ingest_demo_metadata.py                     # localhost:8080
    python datahub/ingest_demo_metadata.py --gms http://host:8080 --token XYZ

Idempotent: re-running overwrites the same URNs.
"""

from __future__ import annotations

import argparse
import sys
import time

from datahub.emitter.mce_builder import (
    make_data_platform_urn,
    make_dataset_urn,
    make_group_urn,
    make_user_urn,
)
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    AuditStampClass,
    DatasetPropertiesClass,
    DeprecationClass,
    GlobalTagsClass,
    OtherSchemaClass,
    OwnerClass,
    OwnershipClass,
    OwnershipTypeClass,
    SchemaFieldClass,
    SchemaFieldDataTypeClass,
    SchemaMetadataClass,
    StringTypeClass,
    TagAssociationClass,
    NumberTypeClass,
    BooleanTypeClass,
    DateTypeClass,
)

PLATFORM_SNOWFLAKE = "snowflake"
PLATFORM_POSTGRES = "postgres"
PLATFORM_KAFKA = "kafka"
ENV = "PROD"

_NOW = int(time.time() * 1000)
_AUDIT = AuditStampClass(time=_NOW, actor="urn:li:corpuser:datahub")


def _field(path: str, native: str, kind: str = "string") -> SchemaFieldClass:
    """One schema column."""
    types = {
        "string": StringTypeClass(),
        "number": NumberTypeClass(),
        "boolean": BooleanTypeClass(),
        "date": DateTypeClass(),
    }
    return SchemaFieldClass(
        fieldPath=path,
        type=SchemaFieldDataTypeClass(type=types[kind]),
        nativeDataType=native,
        nullable=True,
    )


def _schema(name: str, platform: str, fields: list[SchemaFieldClass]) -> SchemaMetadataClass:
    return SchemaMetadataClass(
        schemaName=name,
        platform=make_data_platform_urn(platform),
        version=0,
        hash="",
        platformSchema=OtherSchemaClass(rawSchema=""),
        fields=fields,
        created=_AUDIT,
        lastModified=_AUDIT,
    )


def _ownership(*users: str, groups: tuple[str, ...] = ()) -> OwnershipClass:
    owners = [
        OwnerClass(owner=make_user_urn(u), type=OwnershipTypeClass.TECHNICAL_OWNER)
        for u in users
    ] + [
        OwnerClass(owner=make_group_urn(g), type=OwnershipTypeClass.BUSINESS_OWNER)
        for g in groups
    ]
    return OwnershipClass(owners=owners, lastModified=_AUDIT)


def _tags(*names: str) -> GlobalTagsClass:
    return GlobalTagsClass(
        tags=[TagAssociationClass(tag=f"urn:li:tag:{n}") for n in names]
    )


def build_catalogue() -> list[MetadataChangeProposalWrapper]:
    """Assets chosen so every governance rule fires at least once."""
    mcps: list[MetadataChangeProposalWrapper] = []

    def emit(urn: str, *aspects: object) -> None:
        for aspect in aspects:
            mcps.append(MetadataChangeProposalWrapper(entityUrn=urn, aspect=aspect))

    # --- 1. The headline problem ------------------------------------------------
    # Tier-1 finance table: NO owner, NO description, PII columns, no PII tag.
    # Triggers missing_owner + missing_documentation + untagged_pii.
    fct_payments = make_dataset_urn(PLATFORM_SNOWFLAKE, "finance.fct_payments", ENV)
    emit(
        fct_payments,
        DatasetPropertiesClass(
            name="fct_payments",
            qualifiedName="prod.finance.fct_payments",
            description=None,
            customProperties={"tier": "1", "refresh": "hourly"},
        ),
        _schema(
            "fct_payments",
            PLATFORM_SNOWFLAKE,
            [
                _field("payment_id", "BIGINT", "number"),
                _field("customer_email", "VARCHAR(255)"),
                _field("phone_number", "VARCHAR(32)"),
                _field("amount_minor", "BIGINT", "number"),
                _field("settled_at", "TIMESTAMP", "date"),
            ],
        ),
        _tags("tier-1"),
    )

    # --- 2. Untagged PII on a well-owned asset ----------------------------------
    dim_customer = make_dataset_urn(PLATFORM_SNOWFLAKE, "customers.dim_customer", ENV)
    emit(
        dim_customer,
        DatasetPropertiesClass(
            name="dim_customer",
            qualifiedName="prod.customers.dim_customer",
            description="Master customer dimension, one row per customer.",
        ),
        _ownership("priya.nair", groups=("customer-data",)),
        _schema(
            "dim_customer",
            PLATFORM_SNOWFLAKE,
            [
                _field("customer_id", "BIGINT", "number"),
                _field("email", "VARCHAR(255)"),
                _field("date_of_birth", "DATE", "date"),
                _field("home_address", "VARCHAR(512)"),
            ],
        ),
    )

    # --- 3. Deprecated but still in use -----------------------------------------
    fct_orders_v1 = make_dataset_urn(PLATFORM_SNOWFLAKE, "legacy.fct_orders_v1", ENV)
    emit(
        fct_orders_v1,
        DatasetPropertiesClass(
            name="fct_orders_v1",
            qualifiedName="prod.legacy.fct_orders_v1",
            description="Superseded by fct_orders_v2. Do not build on this.",
        ),
        DeprecationClass(
            deprecated=True,
            note="Replaced by fct_orders_v2 in February.",
            decommissionTime=None,
            actor="urn:li:corpuser:datahub",
        ),
        _schema(
            "fct_orders_v1",
            PLATFORM_SNOWFLAKE,
            [_field("order_id", "BIGINT", "number"), _field("total", "DECIMAL", "number")],
        ),
        _tags("deprecated"),
    )

    # --- 4. Undocumented raw table ----------------------------------------------
    users_raw = make_dataset_urn(PLATFORM_POSTGRES, "app.users_raw", ENV)
    emit(
        users_raw,
        DatasetPropertiesClass(
            name="users_raw", qualifiedName="prod.app.users_raw", description=None
        ),
        _ownership("app-platform"),
        _schema(
            "users_raw",
            PLATFORM_POSTGRES,
            [
                _field("id", "BIGINT", "number"),
                _field("email", "VARCHAR(255)"),
                _field("created_at", "TIMESTAMP", "date"),
            ],
        ),
    )

    # --- 5. Streaming source, unowned -------------------------------------------
    checkout = make_dataset_urn(PLATFORM_KAFKA, "events.checkout_stream", ENV)
    emit(
        checkout,
        DatasetPropertiesClass(
            name="checkout_stream",
            qualifiedName="prod.events.checkout_stream",
            description="Checkout events, 7-day retention.",
        ),
        _schema(
            "checkout_stream",
            PLATFORM_KAFKA,
            [_field("event_id", "STRING"), _field("user_email", "STRING")],
        ),
        _tags("streaming", "tier-1"),
    )

    # --- 6-8. Well-governed assets, so the demo is not uniformly red ------------
    for name, qualified, description, owner in [
        (
            "fct_revenue_daily",
            "prod.finance.fct_revenue_daily",
            "Certified daily revenue rollup powering the executive dashboard.",
            "finance-data",
        ),
        (
            "dim_warehouse",
            "prod.ops.dim_warehouse",
            "Warehouse locations and capacity, refreshed weekly.",
            "ops-analytics",
        ),
        (
            "stg_invoices",
            "prod.analytics.stg_invoices",
            "Staging model normalising invoice line items.",
            "analytics-eng",
        ),
    ]:
        urn = make_dataset_urn(PLATFORM_SNOWFLAKE, qualified.replace("prod.", ""), ENV)
        emit(
            urn,
            DatasetPropertiesClass(
                name=name, qualifiedName=qualified, description=description
            ),
            _ownership(owner),
            _schema(
                name,
                PLATFORM_SNOWFLAKE,
                [_field(f"{name}_id", "BIGINT", "number"), _field("updated_at", "TIMESTAMP", "date")],
            ),
            _tags("certified"),
        )

    return mcps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gms", default="http://localhost:8080", help="GMS base URL")
    parser.add_argument("--token", default=None, help="DataHub personal access token")
    args = parser.parse_args()

    emitter = DatahubRestEmitter(gms_server=args.gms, token=args.token)
    try:
        emitter.test_connection()
    except Exception as exc:  # noqa: BLE001 - report, do not trace
        print(f"Cannot reach DataHub at {args.gms}: {exc}", file=sys.stderr)
        return 1

    mcps = build_catalogue()
    for mcp in mcps:
        emitter.emit(mcp)

    urns = {mcp.entityUrn for mcp in mcps}
    print(f"Emitted {len(mcps)} aspects across {len(urns)} datasets to {args.gms}")
    print("Indexing takes a few seconds; then browse http://localhost:9002")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
