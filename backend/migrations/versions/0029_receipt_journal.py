"""Add a journal-event bridge for new verified receipts.

Revision ID: 0029_receipt_journal
Revises: 0028_org_registry
"""
from alembic import op
import sqlalchemy as sa

revision="0029_receipt_journal"
down_revision="0028_org_registry"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("journal_events",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("event_key",sa.String(160),unique=True,nullable=False),
        sa.Column("source_payment_id",sa.String(36),sa.ForeignKey("payments.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("kind",sa.String(30),nullable=False),
        sa.Column("posted_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("kind IN ('RECEIPT', 'REVERSAL')",name="ck_journal_event_kind"))
    op.create_index("ix_journal_events_payment","journal_events",["source_payment_id"])
    op.create_table("journal_lines",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("event_id",sa.String(36),sa.ForeignKey("journal_events.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("account_code",sa.String(40),nullable=False),
        sa.Column("debit_ugx",sa.BigInteger(),nullable=False),
        sa.Column("credit_ugx",sa.BigInteger(),nullable=False),
        sa.CheckConstraint("debit_ugx >= 0 AND credit_ugx >= 0",name="ck_journal_nonnegative"),
        sa.CheckConstraint("(debit_ugx > 0 AND credit_ugx = 0) OR (credit_ugx > 0 AND debit_ugx = 0)",name="ck_journal_one_side"),
        sa.UniqueConstraint("event_id","account_code",name="uq_journal_account_per_event"))
    op.create_index("ix_journal_lines_event","journal_lines",["event_id"])
    if op.get_bind().dialect.name=="postgresql":
        for table in ("journal_events","journal_lines"):
            op.execute(f"CREATE TRIGGER kats_protect_{table} BEFORE UPDATE OR DELETE ON {table} "
                       "FOR EACH ROW EXECUTE FUNCTION kats_append_only_guard()")

def downgrade():
    if op.get_bind().dialect.name=="postgresql":
        for table in ("journal_lines","journal_events"):
            op.execute(f"DROP TRIGGER IF EXISTS kats_protect_{table} ON {table}")
    op.drop_index("ix_journal_lines_event",table_name="journal_lines")
    op.drop_table("journal_lines")
    op.drop_index("ix_journal_events_payment",table_name="journal_events")
    op.drop_table("journal_events")
