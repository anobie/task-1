"""data quality

Revision ID: 0007_data_quality
Revises: 0006_messaging
Create Date: 2026-04-02 04:20:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_data_quality"
down_revision = "0006_messaging"
branch_labels = None
depends_on = None


def upgrade() -> None:
    quarantine_status = sa.Enum("OPEN", "ACCEPTED", "DISCARDED", name="quarantinestatus", native_enum=False)

    op.create_table(
        "quarantine_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", quarantine_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Integer(), nullable=True),
    )
    op.create_index("ix_quarantine_entries_entity_type", "quarantine_entries", ["entity_type"])
    op.create_index("ix_quarantine_entries_fingerprint", "quarantine_entries", ["fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_quarantine_entries_fingerprint", table_name="quarantine_entries")
    op.drop_index("ix_quarantine_entries_entity_type", table_name="quarantine_entries")
    op.drop_table("quarantine_entries")
    pass
