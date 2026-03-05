"""T7 certificate generation and snapshot baseline

Revision ID: 20260305_0003
Revises: 20260305_0002
Create Date: 2026-03-05 23:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260305_0003"
down_revision = "20260305_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("certificate_number", sa.String(length=32), nullable=False),
        sa.Column("source_application_id", sa.Integer(), nullable=False),
        sa.Column("source_application_number", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("applicant_subject", sa.String(length=255), nullable=False),
        sa.Column("applicant_username", sa.String(length=255), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("generated_by_subject", sa.String(length=255), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["source_application_id"], ["cert_application.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("certificate_number", name="uq_certificate_number"),
        sa.UniqueConstraint("source_application_id", name="uq_certificate_source_application_id"),
    )
    op.create_index("ix_certificate_certificate_number", "certificate", ["certificate_number"])
    op.create_index("ix_certificate_source_application_id", "certificate", ["source_application_id"])
    op.create_index("ix_certificate_source_application_number", "certificate", ["source_application_number"])
    op.create_index("ix_certificate_status", "certificate", ["status"])
    op.create_index("ix_certificate_applicant_subject", "certificate", ["applicant_subject"])

    op.create_table(
        "certificate_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("certificate_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("changed_by_subject", sa.String(length=255), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["certificate_id"], ["certificate.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_certificate_status_history_certificate_id", "certificate_status_history", ["certificate_id"])
    op.create_index("ix_certificate_status_history_to_status", "certificate_status_history", ["to_status"])
    op.create_index("ix_certificate_status_history_changed_at", "certificate_status_history", ["changed_at"])


def downgrade() -> None:
    op.drop_index("ix_certificate_status_history_changed_at", table_name="certificate_status_history")
    op.drop_index("ix_certificate_status_history_to_status", table_name="certificate_status_history")
    op.drop_index("ix_certificate_status_history_certificate_id", table_name="certificate_status_history")
    op.drop_table("certificate_status_history")

    op.drop_index("ix_certificate_applicant_subject", table_name="certificate")
    op.drop_index("ix_certificate_status", table_name="certificate")
    op.drop_index("ix_certificate_source_application_number", table_name="certificate")
    op.drop_index("ix_certificate_source_application_id", table_name="certificate")
    op.drop_index("ix_certificate_certificate_number", table_name="certificate")
    op.drop_table("certificate")
