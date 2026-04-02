"""scope grants

Revision ID: 0009_scope_grants
Revises: 0008_integrations
Create Date: 2026-04-02 17:45:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_scope_grants"
down_revision = "0008_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    scope_type = sa.Enum("ORGANIZATION", "SECTION", name="scopetype", native_enum=False)

    op.create_table(
        "scope_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("scope_type", scope_type, nullable=False),
        sa.Column("scope_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("user_id", "scope_type", "scope_id", name="uq_scope_grant_user_scope"),
    )
    op.create_index("ix_scope_grants_user_id", "scope_grants", ["user_id"])
    op.create_index("ix_scope_grants_scope_id", "scope_grants", ["scope_id"])


def downgrade() -> None:
    op.drop_index("ix_scope_grants_scope_id", table_name="scope_grants")
    op.drop_index("ix_scope_grants_user_id", table_name="scope_grants")
    op.drop_table("scope_grants")
