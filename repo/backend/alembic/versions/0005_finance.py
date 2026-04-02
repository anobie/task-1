"""finance

Revision ID: 0005_finance
Revises: 0004_review_scoring
Create Date: 2026-04-02 03:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_finance"
down_revision = "0004_review_scoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    entry_type = sa.Enum("CHARGE", "PAYMENT", "REFUND", "LATE_FEE", name="entrytype", native_enum=False)
    payment_instrument = sa.Enum("CASH", "CHECK", "INTERNAL_TRANSFER", name="paymentinstrument", native_enum=False)

    op.create_table(
        "ledger_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("student_id"),
    )
    op.create_index("ix_ledger_accounts_student_id", "ledger_accounts", ["student_id"])

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("ledger_accounts.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("entry_type", entry_type, nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("instrument", payment_instrument, nullable=True),
        sa.Column("reference_entry_id", sa.Integer(), sa.ForeignKey("ledger_entries.id"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_ledger_entries_account_id", "ledger_entries", ["account_id"])
    op.create_index("ix_ledger_entries_student_id", "ledger_entries", ["student_id"])

    op.create_table(
        "bank_statement_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_id", sa.String(length=64), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=False),
        sa.Column("raw_line", sa.Text(), nullable=False),
        sa.Column("matched", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("import_id", "line_number", name="uq_statement_import_line"),
    )
    op.create_index("ix_bank_statement_lines_import_id", "bank_statement_lines", ["import_id"])

    op.create_table(
        "reconciliation_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("matched_total", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("unmatched_total", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_reconciliation_reports_import_id", "reconciliation_reports", ["import_id"])


def downgrade() -> None:
    op.drop_index("ix_reconciliation_reports_import_id", table_name="reconciliation_reports")
    op.drop_table("reconciliation_reports")
    op.drop_index("ix_bank_statement_lines_import_id", table_name="bank_statement_lines")
    op.drop_table("bank_statement_lines")
    op.drop_index("ix_ledger_entries_student_id", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_account_id", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index("ix_ledger_accounts_student_id", table_name="ledger_accounts")
    op.drop_table("ledger_accounts")
    pass
