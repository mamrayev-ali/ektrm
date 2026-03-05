"""T8 mock signing, publication, and registry baseline

Revision ID: 20260305_0004
Revises: 20260305_0003
Create Date: 2026-03-05 23:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260305_0004"
down_revision = "20260305_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("certificate", sa.Column("signed_by_subject", sa.String(length=255), nullable=True))
    op.add_column("certificate", sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("certificate", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_certificate_published_at", "certificate", ["published_at"])

    op.create_table(
        "certificate_registry_publication",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("certificate_id", sa.Integer(), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_by_subject", sa.String(length=255), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["certificate_id"], ["certificate.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_certificate_registry_publication_certificate_id", "certificate_registry_publication", ["certificate_id"])
    op.create_index("ix_certificate_registry_publication_visibility", "certificate_registry_publication", ["visibility"])
    op.create_index("ix_certificate_registry_publication_is_public", "certificate_registry_publication", ["is_public"])
    op.create_index("ix_certificate_registry_publication_published_at", "certificate_registry_publication", ["published_at"])


def downgrade() -> None:
    op.drop_index("ix_certificate_registry_publication_published_at", table_name="certificate_registry_publication")
    op.drop_index("ix_certificate_registry_publication_is_public", table_name="certificate_registry_publication")
    op.drop_index("ix_certificate_registry_publication_visibility", table_name="certificate_registry_publication")
    op.drop_index("ix_certificate_registry_publication_certificate_id", table_name="certificate_registry_publication")
    op.drop_table("certificate_registry_publication")

    op.drop_index("ix_certificate_published_at", table_name="certificate")
    op.drop_column("certificate", "published_at")
    op.drop_column("certificate", "signed_at")
    op.drop_column("certificate", "signed_by_subject")
