"""Add certificate signature operations for OPS ECP flow

Revision ID: 20260312_0007
Revises: 20260311_0006
Create Date: 2026-03-12 18:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260312_0007"
down_revision = "20260311_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificate_signature",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operation_id", sa.String(length=64), nullable=False),
        sa.Column("certificate_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_subject", sa.String(length=255), nullable=False),
        sa.Column(
            "signer_kind",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'signAny'"),
        ),
        sa.Column("signature_mode", sa.String(length=16), nullable=False),
        sa.Column("payload_base64", sa.Text(), nullable=False),
        sa.Column("payload_sha256_hex", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("signature_cms_base64", sa.Text(), nullable=True),
        sa.Column("signer_certificate_subject", sa.Text(), nullable=True),
        sa.Column("signer_certificate_serial_number", sa.String(length=255), nullable=True),
        sa.Column("signer_iin", sa.String(length=32), nullable=True),
        sa.Column("signer_bin", sa.String(length=32), nullable=True),
        sa.Column("validation_result", sa.String(length=32), nullable=False),
        sa.Column("validation_error_code", sa.String(length=64), nullable=True),
        sa.Column("revocation_check_mode", sa.String(length=32), nullable=True),
        sa.Column("validator_name", sa.String(length=64), nullable=True),
        sa.Column("client_meta_json", sa.Text(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["certificate_id"], ["certificate.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("operation_id", name="uq_certificate_signature_operation_id"),
    )
    op.create_index("ix_certificate_signature_certificate_id", "certificate_signature", ["certificate_id"])
    op.create_index("ix_certificate_signature_operation_id", "certificate_signature", ["operation_id"])
    op.create_index("ix_certificate_signature_payload_sha256_hex", "certificate_signature", ["payload_sha256_hex"])
    op.create_index("ix_certificate_signature_requested_by_subject", "certificate_signature", ["requested_by_subject"])
    op.create_index("ix_certificate_signature_signer_iin", "certificate_signature", ["signer_iin"])
    op.create_index("ix_certificate_signature_signer_bin", "certificate_signature", ["signer_bin"])
    op.create_index("ix_certificate_signature_validation_result", "certificate_signature", ["validation_result"])
    op.create_index("ix_certificate_signature_validation_error_code", "certificate_signature", ["validation_error_code"])
    op.create_index("ix_certificate_signature_validated_at", "certificate_signature", ["validated_at"])


def downgrade() -> None:
    op.drop_index("ix_certificate_signature_validated_at", table_name="certificate_signature")
    op.drop_index("ix_certificate_signature_validation_error_code", table_name="certificate_signature")
    op.drop_index("ix_certificate_signature_validation_result", table_name="certificate_signature")
    op.drop_index("ix_certificate_signature_signer_bin", table_name="certificate_signature")
    op.drop_index("ix_certificate_signature_signer_iin", table_name="certificate_signature")
    op.drop_index("ix_certificate_signature_requested_by_subject", table_name="certificate_signature")
    op.drop_index("ix_certificate_signature_payload_sha256_hex", table_name="certificate_signature")
    op.drop_index("ix_certificate_signature_operation_id", table_name="certificate_signature")
    op.drop_index("ix_certificate_signature_certificate_id", table_name="certificate_signature")
    op.drop_table("certificate_signature")
