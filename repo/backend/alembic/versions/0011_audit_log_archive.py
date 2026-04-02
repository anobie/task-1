"""audit log archive table

Revision ID: 0011_audit_log_archive
Revises: 0010_encrypt_integration_secrets
Create Date: 2026-04-02 21:10:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_audit_log_archive"
down_revision = "0010_encrypt_integration_secrets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs_archive",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("original_audit_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_name", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("before_hash", sa.String(length=64), nullable=True),
        sa.Column("after_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("original_audit_id", name="uq_audit_logs_archive_original_audit_id"),
    )
    op.create_index("ix_audit_logs_archive_original_audit_id", "audit_logs_archive", ["original_audit_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_archive_original_audit_id", table_name="audit_logs_archive")
    op.drop_table("audit_logs_archive")
