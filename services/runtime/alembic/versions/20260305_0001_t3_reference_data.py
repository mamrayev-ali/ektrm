"""T3 reference data and lookup registries

Revision ID: 20260305_0001
Revises:
Create Date: 2026-03-05 18:10:00
"""

from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.seed.reference_data_seed import (
    ACCREDITATION_ATTESTATS_SEED,
    MANDATORY_DICTIONARIES,
    MANDATORY_DICTIONARY_ITEMS,
    OPS_REGISTRY_SEED,
)


# revision identifiers, used by Alembic.
revision = "20260305_0001"
down_revision = None
branch_labels = None
depends_on = None


reference_dictionaries = sa.table(
    "reference_dictionaries",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
    sa.column("is_active", sa.Boolean),
)

reference_dictionary_items = sa.table(
    "reference_dictionary_items",
    sa.column("dictionary_id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("name", sa.Text),
    sa.column("sort_order", sa.Integer),
    sa.column("legal_basis", sa.Text),
    sa.column("is_active", sa.Boolean),
)

ops_registry = sa.table(
    "ops_registry",
    sa.column("ops_code", sa.String),
    sa.column("full_name", sa.Text),
    sa.column("bin", sa.String),
    sa.column("accreditation_attestat_number", sa.String),
    sa.column("head_name", sa.String),
    sa.column("city", sa.String),
    sa.column("is_active", sa.Boolean),
)

accreditation_attestats = sa.table(
    "accreditation_attestats",
    sa.column("attestat_number", sa.String),
    sa.column("ops_code", sa.String),
    sa.column("issued_at", sa.Date),
    sa.column("expires_at", sa.Date),
    sa.column("status", sa.String),
    sa.column("scope_summary", sa.Text),
    sa.column("is_active", sa.Boolean),
)


def _seed(connection: sa.Connection) -> None:
    if context.is_offline_mode():
        return

    for entry in MANDATORY_DICTIONARIES:
        stmt = postgresql.insert(reference_dictionaries).values(
            code=entry["code"],
            name=entry["name"],
            description=entry["description"],
            is_active=True,
        )
        connection.execute(stmt.on_conflict_do_nothing(index_elements=["code"]))

    dictionary_ids = {
        row.code: row.id
        for row in connection.execute(
            sa.select(reference_dictionaries.c.id, reference_dictionaries.c.code)
        ).all()
    }

    for item in MANDATORY_DICTIONARY_ITEMS:
        dictionary_id = dictionary_ids[item["dictionary_code"]]
        stmt = postgresql.insert(reference_dictionary_items).values(
            dictionary_id=dictionary_id,
            code=item["code"],
            name=item["name"],
            sort_order=item["sort_order"],
            legal_basis=item["legal_basis"],
            is_active=True,
        )
        connection.execute(
            stmt.on_conflict_do_nothing(index_elements=["dictionary_id", "code"])
        )

    for entry in OPS_REGISTRY_SEED:
        stmt = postgresql.insert(ops_registry).values(
            ops_code=entry["ops_code"],
            full_name=entry["full_name"],
            bin=entry["bin"],
            accreditation_attestat_number=entry["accreditation_attestat_number"],
            head_name=entry["head_name"],
            city=entry["city"],
            is_active=True,
        )
        connection.execute(stmt.on_conflict_do_nothing(index_elements=["ops_code"]))

    for entry in ACCREDITATION_ATTESTATS_SEED:
        stmt = postgresql.insert(accreditation_attestats).values(
            attestat_number=entry["attestat_number"],
            ops_code=entry["ops_code"],
            issued_at=entry["issued_at"],
            expires_at=entry["expires_at"],
            status=entry["status"],
            scope_summary=entry["scope_summary"],
            is_active=True,
        )
        connection.execute(stmt.on_conflict_do_nothing(index_elements=["attestat_number"]))


def upgrade() -> None:
    op.create_table(
        "reference_dictionaries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("code", name="uq_reference_dictionaries_code"),
    )

    op.create_table(
        "reference_dictionary_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dictionary_id", sa.Integer, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("100")),
        sa.Column("legal_basis", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["dictionary_id"], ["reference_dictionaries.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dictionary_id", "code", name="uq_reference_dictionary_item_code"),
    )
    op.create_index(
        "ix_reference_dictionary_items_dictionary_id",
        "reference_dictionary_items",
        ["dictionary_id"],
    )

    op.create_table(
        "ops_registry",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ops_code", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("bin", sa.String(length=12), nullable=False),
        sa.Column("accreditation_attestat_number", sa.String(length=64), nullable=False),
        sa.Column("head_name", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("ops_code", name="uq_ops_registry_ops_code"),
        sa.UniqueConstraint("bin", name="uq_ops_registry_bin"),
    )
    op.create_index("ix_ops_registry_ops_code", "ops_registry", ["ops_code"])
    op.create_index(
        "ix_ops_registry_accreditation_attestat_number",
        "ops_registry",
        ["accreditation_attestat_number"],
    )

    op.create_table(
        "accreditation_attestats",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("attestat_number", sa.String(length=64), nullable=False),
        sa.Column("ops_code", sa.String(length=32), nullable=False),
        sa.Column("issued_at", sa.Date, nullable=False),
        sa.Column("expires_at", sa.Date, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scope_summary", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("attestat_number", name="uq_accreditation_attestats_attestat_number"),
    )
    op.create_index("ix_accreditation_attestats_attestat_number", "accreditation_attestats", ["attestat_number"])
    op.create_index("ix_accreditation_attestats_ops_code", "accreditation_attestats", ["ops_code"])
    op.create_index("ix_accreditation_attestats_status", "accreditation_attestats", ["status"])

    _seed(op.get_bind())


def downgrade() -> None:
    op.drop_index("ix_accreditation_attestats_status", table_name="accreditation_attestats")
    op.drop_index("ix_accreditation_attestats_ops_code", table_name="accreditation_attestats")
    op.drop_index("ix_accreditation_attestats_attestat_number", table_name="accreditation_attestats")
    op.drop_table("accreditation_attestats")

    op.drop_index("ix_ops_registry_accreditation_attestat_number", table_name="ops_registry")
    op.drop_index("ix_ops_registry_ops_code", table_name="ops_registry")
    op.drop_table("ops_registry")

    op.drop_index("ix_reference_dictionary_items_dictionary_id", table_name="reference_dictionary_items")
    op.drop_table("reference_dictionary_items")
    op.drop_table("reference_dictionaries")
