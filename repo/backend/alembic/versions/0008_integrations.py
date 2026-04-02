"""integrations

Revision ID: 0008_integrations
Revises: 0007_data_quality
Create Date: 2026-04-02 05:10:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_integrations"
down_revision = "0007_data_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("secret_key", sa.String(length=128), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("client_id"),
    )
    op.create_index("ix_integration_clients_client_id", "integration_clients", ["client_id"])

    op.create_table(
        "nonce_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("nonce", sa.String(length=120), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body_hash", sa.String(length=64), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("client_id", "nonce", name="uq_nonce_per_client"),
    )
    op.create_index("ix_nonce_logs_client_id", "nonce_logs", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_nonce_logs_client_id", table_name="nonce_logs")
    op.drop_table("nonce_logs")
    op.drop_index("ix_integration_clients_client_id", table_name="integration_clients")
    op.drop_table("integration_clients")
