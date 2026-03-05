"""T4 order3 domain model and state history

Revision ID: 20260305_0002
Revises: 20260305_0001
Create Date: 2026-03-05 21:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260305_0002"
down_revision = "20260305_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cert_application",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_number", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("applicant_subject", sa.String(length=255), nullable=False),
        sa.Column("applicant_username", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("application_number", name="uq_cert_application_number"),
    )
    op.create_index("ix_cert_application_application_number", "cert_application", ["application_number"])
    op.create_index("ix_cert_application_status", "cert_application", ["status"])
    op.create_index("ix_cert_application_applicant_subject", "cert_application", ["applicant_subject"])

    op.create_table(
        "cert_application_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["application_id"], ["cert_application.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_cert_application_status_history_application_id",
        "cert_application_status_history",
        ["application_id"],
    )
    op.create_index(
        "ix_cert_application_status_history_to_status",
        "cert_application_status_history",
        ["to_status"],
    )
    op.create_index(
        "ix_cert_application_status_history_changed_at",
        "cert_application_status_history",
        ["changed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cert_application_status_history_changed_at", table_name="cert_application_status_history")
    op.drop_index("ix_cert_application_status_history_to_status", table_name="cert_application_status_history")
    op.drop_index("ix_cert_application_status_history_application_id", table_name="cert_application_status_history")
    op.drop_table("cert_application_status_history")

    op.drop_index("ix_cert_application_applicant_subject", table_name="cert_application")
    op.drop_index("ix_cert_application_status", table_name="cert_application")
    op.drop_index("ix_cert_application_application_number", table_name="cert_application")
    op.drop_table("cert_application")
