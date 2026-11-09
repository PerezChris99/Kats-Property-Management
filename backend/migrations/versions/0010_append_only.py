"""Immutable financial and audit event history at the database boundary.

Database-level triggers block update/delete of historical facts in PostgreSQL.
Application runtime must reverse events with new ledger rows, never rewrite them.
"""
from alembic import op
import sqlalchemy as sa

revision="0010_append_only"
down_revision="0009_outbox_retry"
branch_labels=None
depends_on=None

def upgrade():
    op.create_index("uq_ledger_payment_event","ledger_entries",["payment_id","event"],
        unique=True,postgresql_where=sa.text("payment_id IS NOT NULL"),
        sqlite_where=sa.text("payment_id IS NOT NULL"))
    if op.get_bind().dialect.name=="postgresql":
        op.execute("""
        CREATE FUNCTION kats_append_only_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'Kats financial/audit history is append-only. Use a reversal event.';
        END; $$;
        """)
        for table in ("ledger_entries","payments","invoices","audit_logs",
                      "room_state_history","credit_notes","deposit_movements",
                      "lease_amendments","inspections"):
            ops="UPDATE OR DELETE" if table in (
                "ledger_entries","audit_logs","room_state_history",
                "credit_notes","lease_amendments","inspections") else "DELETE"
            op.execute(f"CREATE TRIGGER kats_protect_{table} BEFORE {ops} ON {table} "
                       "FOR EACH ROW EXECUTE FUNCTION kats_append_only_guard()")

def downgrade():
    if op.get_bind().dialect.name=="postgresql":
        for table in ("ledger_entries","payments","invoices","audit_logs",
                      "room_state_history","credit_notes","deposit_movements",
                      "lease_amendments","inspections"):
            op.execute(f"DROP TRIGGER IF EXISTS kats_protect_{table} ON {table}")
        op.execute("DROP FUNCTION IF EXISTS kats_append_only_guard()")
    op.drop_index("uq_ledger_payment_event",table_name="ledger_entries")
