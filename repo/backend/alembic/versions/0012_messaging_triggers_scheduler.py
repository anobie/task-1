"""messaging trigger scheduler

Revision ID: 0012_messaging_triggers_scheduler
Revises: 0011_audit_log_archive
Create Date: 2026-04-02 22:30:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_messaging_triggers_scheduler"
down_revision = "0011_audit_log_archive"
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
    schedule_status_enum = sa.Enum(
        "PENDING",
        "DISPATCHED",
        "CANCELLED",
        name="notificationschedulestatus",
        native_enum=False,
    )

    op.create_table(
        "notification_trigger_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trigger_type", trigger_enum, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("lead_hours", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("trigger_type", name="uq_notification_trigger_configs_trigger_type"),
    )

    op.create_table(
        "notification_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trigger_type", trigger_enum, nullable=False),
        sa.Column("status", schedule_status_enum, nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_notification_schedules_recipient_id", "notification_schedules", ["recipient_id"])
    op.create_index("ix_notification_schedules_due_at", "notification_schedules", ["due_at"])

    op.bulk_insert(
        sa.table(
            "notification_trigger_configs",
            sa.column("trigger_type", trigger_enum),
            sa.column("enabled", sa.Boolean()),
            sa.column("lead_hours", sa.Integer()),
        ),
        [
            {"trigger_type": "ASSIGNMENT_POSTED", "enabled": True, "lead_hours": None},
            {"trigger_type": "DEADLINE_72H", "enabled": True, "lead_hours": 72},
            {"trigger_type": "DEADLINE_24H", "enabled": True, "lead_hours": 24},
            {"trigger_type": "DEADLINE_2H", "enabled": True, "lead_hours": 2},
            {"trigger_type": "GRADING_COMPLETED", "enabled": True, "lead_hours": None},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_schedules_due_at", table_name="notification_schedules")
    op.drop_index("ix_notification_schedules_recipient_id", table_name="notification_schedules")
    op.drop_table("notification_schedules")
    op.drop_table("notification_trigger_configs")
