"""T9 post-issuance suspend and terminate baseline

Revision ID: 20260306_0005
Revises: 20260305_0004
Create Date: 2026-03-06 10:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260306_0005"
down_revision = "20260305_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "certificate",
        sa.Column("is_dangerous_product", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_certificate_is_dangerous_product", "certificate", ["is_dangerous_product"])

    op.create_table(
        "post_issuance_application",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_number", sa.String(length=32), nullable=False),
        sa.Column("source_certificate_id", sa.Integer(), nullable=False),
        sa.Column("source_certificate_number", sa.String(length=32), nullable=False),
        sa.Column("source_application_id", sa.Integer(), nullable=False),
        sa.Column("source_application_number", sa.String(length=32), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("initiator_role", sa.String(length=32), nullable=False),
        sa.Column("applicant_subject", sa.String(length=255), nullable=False),
        sa.Column("applicant_username", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["source_certificate_id"], ["certificate.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_application_id"], ["cert_application.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("application_number", name="uq_post_issuance_application_number"),
    )
    op.create_index("ix_post_issuance_application_application_number", "post_issuance_application", ["application_number"])
    op.create_index("ix_post_issuance_application_source_certificate_id", "post_issuance_application", ["source_certificate_id"])
    op.create_index("ix_post_issuance_application_source_certificate_number", "post_issuance_application", ["source_certificate_number"])
    op.create_index("ix_post_issuance_application_source_application_id", "post_issuance_application", ["source_application_id"])
    op.create_index("ix_post_issuance_application_source_application_number", "post_issuance_application", ["source_application_number"])
    op.create_index("ix_post_issuance_application_action_type", "post_issuance_application", ["action_type"])
    op.create_index("ix_post_issuance_application_status", "post_issuance_application", ["status"])
    op.create_index("ix_post_issuance_application_initiator_role", "post_issuance_application", ["initiator_role"])
    op.create_index("ix_post_issuance_application_applicant_subject", "post_issuance_application", ["applicant_subject"])

    op.create_table(
        "post_issuance_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_issuance_application_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["post_issuance_application_id"], ["post_issuance_application.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_post_issuance_status_history_post_issuance_application_id",
        "post_issuance_status_history",
        ["post_issuance_application_id"],
    )
    op.create_index("ix_post_issuance_status_history_to_status", "post_issuance_status_history", ["to_status"])
    op.create_index("ix_post_issuance_status_history_changed_at", "post_issuance_status_history", ["changed_at"])


def downgrade() -> None:
    op.drop_index("ix_post_issuance_status_history_changed_at", table_name="post_issuance_status_history")
    op.drop_index("ix_post_issuance_status_history_to_status", table_name="post_issuance_status_history")
    op.drop_index(
        "ix_post_issuance_status_history_post_issuance_application_id",
        table_name="post_issuance_status_history",
    )
    op.drop_table("post_issuance_status_history")

    op.drop_index("ix_post_issuance_application_applicant_subject", table_name="post_issuance_application")
    op.drop_index("ix_post_issuance_application_initiator_role", table_name="post_issuance_application")
    op.drop_index("ix_post_issuance_application_status", table_name="post_issuance_application")
    op.drop_index("ix_post_issuance_application_action_type", table_name="post_issuance_application")
    op.drop_index("ix_post_issuance_application_source_application_number", table_name="post_issuance_application")
    op.drop_index("ix_post_issuance_application_source_application_id", table_name="post_issuance_application")
    op.drop_index("ix_post_issuance_application_source_certificate_number", table_name="post_issuance_application")
    op.drop_index("ix_post_issuance_application_source_certificate_id", table_name="post_issuance_application")
    op.drop_index("ix_post_issuance_application_application_number", table_name="post_issuance_application")
    op.drop_table("post_issuance_application")

    op.drop_index("ix_certificate_is_dangerous_product", table_name="certificate")
    op.drop_column("certificate", "is_dangerous_product")
