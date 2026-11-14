"""Correct deferred general-ledger trigger after 0032 deployment.

Revision ID: 0033_gl_trigger_repair
Revises: 0032_general_ledger

PL/pgSQL CASE evaluated references for two unrelated trigger-row shapes.
For gl_events, NEW.event_id does not exist. IF branches access only the
corresponding record shape. This is a forward-only functional repair and
does not alter or backfill financial data.
"""
from alembic import op

revision = "0033_gl_trigger_repair"
down_revision = "0032_general_ledger"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        CREATE OR REPLACE FUNCTION kats_validate_gl_event()
        RETURNS trigger
        LANGUAGE plpgsql AS $gl_balanced$
        DECLARE
          target_id text;
          amount_dr bigint;
          amount_cr bigint;
          line_count integer;
        BEGIN
          IF TG_TABLE_NAME = 'gl_events' THEN
            target_id := NEW.id;
          ELSIF TG_TABLE_NAME = 'gl_lines' THEN
            target_id := NEW.event_id;
          ELSE
            RAISE EXCEPTION 'Invalid general-ledger trigger table %', TG_TABLE_NAME;
          END IF;
          SELECT count(*), coalesce(sum(debit_ugx),0), coalesce(sum(credit_ugx),0)
          INTO line_count, amount_dr, amount_cr
          FROM gl_lines WHERE event_id=target_id;
          IF line_count < 2 OR amount_dr <> amount_cr OR amount_dr <= 0 THEN
            RAISE EXCEPTION USING MESSAGE='Unbalanced general ledger event ' || target_id;
          END IF;
          RETURN NEW;
        END;
        $gl_balanced$;
        """)


def downgrade():
    # Never restore the broken trigger: a downgrade must not silently make
    # live financial approval paths invalid. Migration remains reversible in
    # metadata only; restore a validated schema backup to roll back.
    pass
