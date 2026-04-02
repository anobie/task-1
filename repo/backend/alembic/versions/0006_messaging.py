"""messaging

Revision ID: 0006_messaging
Revises: 0005_finance
Create Date: 2026-04-02 03:40:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_messaging"
down_revision = "0005_finance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    trigger_enum = sa.Enum(
        "ASSIGNMENT_POSTED",
        "DEADLINE_72H",
        "DEADLINE_24H",
        "DEADLINE_2H",
        "GRADING_COMPLETED",
        name="notificationtrigger",
        native_enum=False,
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trigger_type", trigger_enum, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notifications_recipient_id", "notifications", ["recipient_id"])

    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("notification_id", sa.Integer(), sa.ForeignKey("notifications.id"), nullable=False),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
    )
    op.create_index("ix_notification_logs_notification_id", "notification_logs", ["notification_id"])
    op.create_index("ix_notification_logs_recipient_id", "notification_logs", ["recipient_id"])


def downgrade() -> None:
    op.drop_index("ix_notification_logs_recipient_id", table_name="notification_logs")
    op.drop_index("ix_notification_logs_notification_id", table_name="notification_logs")
    op.drop_table("notification_logs")
    op.drop_index("ix_notifications_recipient_id", table_name="notifications")
    op.drop_table("notifications")
    pass
