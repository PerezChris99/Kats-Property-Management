"""Preserve imported financial statement header evidence and reviewer decisions.

Revision ID: 0035_bank_statement_guard
Revises: 0034_bank_reconciliation

A matching statement can be closed exactly once. Bank identity, date range,
financial balances, hash and importer cannot be rewritten in SQL, even by an
authenticated finance role. Changes must be entered as separately reviewed
corrections instead of mutating historical evidence.
"""
from alembic import op

revision = "0035_bank_statement_guard"
down_revision = "0034_bank_reconciliation"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION kats_guard_bank_statement_evidence()
            RETURNS trigger LANGUAGE plpgsql AS $bank_evidence$
            BEGIN
              IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Imported bank statement evidence cannot be deleted';
              END IF;
              IF OLD.state <> 'OPEN' OR NEW.state <> 'RECONCILED' THEN
                RAISE EXCEPTION 'Bank statement changes require one reviewed close';
              END IF;
              IF ROW(NEW.bank_label, NEW.account_mask, NEW.start_date, NEW.end_date,
                     NEW.opening_ugx, NEW.closing_ugx, NEW.content_sha256,
                     NEW.imported_by, NEW.imported_at)
                 IS DISTINCT FROM
                 ROW(OLD.bank_label, OLD.account_mask, OLD.start_date, OLD.end_date,
                     OLD.opening_ugx, OLD.closing_ugx, OLD.content_sha256,
                     OLD.imported_by, OLD.imported_at) THEN
                RAISE EXCEPTION 'Bank statement source evidence is immutable';
              END IF;
              IF NEW.closed_by IS NULL OR NEW.closed_at IS NULL THEN
                RAISE EXCEPTION 'An independent reviewed closure is required';
              END IF;
              RETURN NEW;
            END;
            $bank_evidence$;
        """)
        op.execute("""
            CREATE TRIGGER kats_immutable_bank_statement_evidence
            BEFORE UPDATE OR DELETE ON bank_statements FOR EACH ROW
            EXECUTE FUNCTION kats_guard_bank_statement_evidence()
        """)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS kats_immutable_bank_statement_evidence ON bank_statements")
        op.execute("DROP FUNCTION IF EXISTS kats_guard_bank_statement_evidence()")
