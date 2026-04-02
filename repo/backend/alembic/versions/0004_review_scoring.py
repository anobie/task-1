"""review scoring

Revision ID: 0004_review_scoring
Revises: 0003_registration
Create Date: 2026-04-02 02:10:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_review_scoring"
down_revision = "0003_registration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    review_status = sa.Enum("DRAFT", "ACTIVE", "CLOSED", name="reviewroundstatus", native_enum=False)
    identity_mode = sa.Enum("BLIND", "SEMI_BLIND", "OPEN", name="identitymode", native_enum=False)
    recheck_status = sa.Enum("REQUESTED", "ASSIGNED", "RESOLVED", name="recheckstatus", native_enum=False)

    op.create_table(
        "scoring_forms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "review_rounds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("term_id", sa.Integer(), sa.ForeignKey("terms.id"), nullable=False),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id"), nullable=False),
        sa.Column("scoring_form_id", sa.Integer(), sa.ForeignKey("scoring_forms.id"), nullable=False),
        sa.Column("identity_mode", identity_mode, nullable=False),
        sa.Column("status", review_status, nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "reviewer_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("round_id", sa.Integer(), sa.ForeignKey("review_rounds.id"), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id"), nullable=False),
        sa.Column("assigned_manually", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("round_id", "reviewer_id", "student_id", name="uq_assignment_round_reviewer_student"),
    )
    op.create_index("ix_reviewer_assignments_round_id", "reviewer_assignments", ["round_id"])
    op.create_index("ix_reviewer_assignments_reviewer_id", "reviewer_assignments", ["reviewer_id"])
    op.create_index("ix_reviewer_assignments_student_id", "reviewer_assignments", ["student_id"])

    op.create_table(
        "scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("reviewer_assignments.id"), nullable=False),
        sa.Column("criterion_scores", sa.JSON(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("assignment_id", name="uq_score_assignment"),
    )
    op.create_index("ix_scores_assignment_id", "scores", ["assignment_id"])

    op.create_table(
        "outlier_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("round_id", sa.Integer(), sa.ForeignKey("review_rounds.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("score_id", sa.Integer(), sa.ForeignKey("scores.id"), nullable=False),
        sa.Column("median_score", sa.Float(), nullable=False),
        sa.Column("deviation", sa.Float(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_outlier_flags_round_id", "outlier_flags", ["round_id"])
    op.create_index("ix_outlier_flags_student_id", "outlier_flags", ["student_id"])

    op.create_table(
        "recheck_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("round_id", sa.Integer(), sa.ForeignKey("review_rounds.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id"), nullable=False),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", recheck_status, nullable=False),
        sa.Column("assigned_reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("recheck_requests")
    op.drop_index("ix_outlier_flags_student_id", table_name="outlier_flags")
    op.drop_index("ix_outlier_flags_round_id", table_name="outlier_flags")
    op.drop_table("outlier_flags")
    op.drop_index("ix_scores_assignment_id", table_name="scores")
    op.drop_table("scores")
    op.drop_index("ix_reviewer_assignments_student_id", table_name="reviewer_assignments")
    op.drop_index("ix_reviewer_assignments_reviewer_id", table_name="reviewer_assignments")
    op.drop_index("ix_reviewer_assignments_round_id", table_name="reviewer_assignments")
    op.drop_table("reviewer_assignments")
    op.drop_table("review_rounds")
    op.drop_table("scoring_forms")
    pass
