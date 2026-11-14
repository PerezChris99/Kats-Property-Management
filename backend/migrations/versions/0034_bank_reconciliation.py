"""Import and review actual bank statements without inventing settlement.

Revision ID: 0034_bank_reconciliation
Revises: 0033_gl_trigger_repair
"""
from alembic import op
import sqlalchemy as sa

revision = "0034_bank_reconciliation"
down_revision = "0033_gl_trigger_repair"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("bank_statements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("bank_label", sa.String(120), nullable=False),
        sa.Column("account_mask", sa.String(30), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("opening_ugx", sa.BigInteger(), nullable=False),
        sa.Column("closing_ugx", sa.BigInteger(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("imported_by", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("closed_by", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("state IN ('OPEN','RECONCILED')", name="ck_bank_statement_state"),
        sa.CheckConstraint("end_date >= start_date", name="ck_bank_statement_dates"))
    op.create_table("bank_statement_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("statement_id", sa.String(36),
                  sa.ForeignKey("bank_statements.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("booked_on", sa.Date(), nullable=False),
        sa.Column("reference", sa.String(160), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("signed_ugx", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("statement_id", "row_number", name="uq_bank_statement_row"),
        sa.CheckConstraint("signed_ugx <> 0", name="ck_bank_line_nonzero"))
    op.create_index("ix_bank_statement_lines_statement_id", "bank_statement_lines", ["statement_id"])
    op.create_table("bank_reconciliation_matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("statement_line_id", sa.String(36),
                  sa.ForeignKey("bank_statement_lines.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("gl_event_id", sa.String(36),
                  sa.ForeignKey("gl_events.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("signed_ugx", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(15), nullable=False),
        sa.Column("proposed_by", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reviewed_by", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("statement_line_id", "gl_event_id", name="uq_bank_match_source"),
        sa.CheckConstraint("signed_ugx <> 0", name="ck_bank_match_nonzero"),
        sa.CheckConstraint("state IN ('PROPOSED','APPROVED','REJECTED')", name="ck_bank_match_state"))
    op.create_index("ix_bank_reconciliation_matches_statement_line_id",
                    "bank_reconciliation_matches", ["statement_line_id"])
    op.create_index("ix_bank_reconciliation_matches_gl_event_id",
                    "bank_reconciliation_matches", ["gl_event_id"])
    if op.get_bind().dialect.name == "postgresql":
        # Financial statements are not visible to tenants/managers. PostgreSQL
        # mirrors Flask's role ceilings and prevents accidental unrestricted
        # data access from newly added API endpoints.
        for table in ("bank_statements", "bank_statement_lines", "bank_reconciliation_matches"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            op.execute(f"CREATE POLICY kats_bank_finance ON {table} "
                       "USING (current_setting('kats.actor_role', true) "
                       "IN ('OWNER','ACCOUNTANT','SUPER_ADMIN','SERVICE')) "
                       "WITH CHECK (current_setting('kats.actor_role', true) "
                       "IN ('OWNER','ACCOUNTANT','SUPER_ADMIN','SERVICE'))")
        op.execute("CREATE TRIGGER kats_immutable_bank_statement_lines "
                   "BEFORE UPDATE OR DELETE ON bank_statement_lines "
                   "FOR EACH ROW EXECUTE FUNCTION kats_append_only_guard()")
        op.execute("""
            CREATE FUNCTION kats_guard_bank_match_review() RETURNS trigger
            LANGUAGE plpgsql AS $bank_match$
            BEGIN
                IF OLD.state IN ('APPROVED','REJECTED') THEN
                    RAISE EXCEPTION 'Bank match decision is immutable';
                END IF;
                IF NEW.statement_line_id <> OLD.statement_line_id
                   OR NEW.gl_event_id <> OLD.gl_event_id
                   OR NEW.signed_ugx <> OLD.signed_ugx
                   OR NEW.proposed_by <> OLD.proposed_by THEN
                    RAISE EXCEPTION 'Bank match source cannot be changed';
                END IF;
                RETURN NEW;
            END;
            $bank_match$;
        """)
        op.execute("CREATE TRIGGER kats_guard_bank_match_review_update "
                   "BEFORE UPDATE OR DELETE ON bank_reconciliation_matches "
                   "FOR EACH ROW EXECUTE FUNCTION kats_guard_bank_match_review()")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS kats_guard_bank_match_review_update "
                   "ON bank_reconciliation_matches")
        op.execute("DROP FUNCTION IF EXISTS kats_guard_bank_match_review()")
        op.execute("DROP TRIGGER IF EXISTS kats_immutable_bank_statement_lines "
                   "ON bank_statement_lines")
    op.drop_index("ix_bank_reconciliation_matches_gl_event_id", table_name="bank_reconciliation_matches")
    op.drop_index("ix_bank_reconciliation_matches_statement_line_id", table_name="bank_reconciliation_matches")
    op.drop_table("bank_reconciliation_matches")
    op.drop_index("ix_bank_statement_lines_statement_id", table_name="bank_statement_lines")
    op.drop_table("bank_statement_lines")
    op.drop_table("bank_statements")
