"""Canonical balanced UGX general ledger, period closures and opening batches.

Revision ID: 0032_general_ledger
Revises: 0031_property_assets
"""
from alembic import op
import sqlalchemy as sa

revision = "0032_general_ledger"
down_revision = "0031_property_assets"
branch_labels = None
depends_on = None

COA = (
    ("CASH_CLEARING","Cash and mobile/bank receipts awaiting external reconciliation","ASSET"),
    ("BANK","Externally reconciled bank funds","ASSET"),
    ("RENT_RECEIVABLE","Tenant receivables","ASSET"),
    ("OTHER_RECEIVABLE","Other receivables","ASSET"),
    ("PREPAID_EXPENSE","Prepaid expenses","ASSET"),
    ("FIXED_ASSETS","Property fixed assets","ASSET"),
    ("ACCOUNTS_PAYABLE","Vendor and operating payables","LIABILITY"),
    ("TENANT_DEPOSITS","Tenant security deposit liability","LIABILITY"),
    ("DEPOSIT_REFUNDS_PAYABLE","Approved deposit refunds awaiting payout proof","LIABILITY"),
    ("ACCRUED_EXPENSES","Accrued expenses","LIABILITY"),
    ("TAX_PAYABLE","Tax payable","LIABILITY"),
    ("OWNER_EQUITY","Owner's equity","EQUITY"),
    ("RETAINED_EARNINGS","Retained earnings","EQUITY"),
    ("RENTAL_INCOME","Earned rental income","REVENUE"),
    ("UTILITY_RECOVERY","Utilities billed to tenants","REVENUE"),
    ("LATE_FEES","Authorized late fees","REVENUE"),
    ("OTHER_INCOME","Other property income","REVENUE"),
    ("REVENUE_CREDITS","Unallocated credit notes (contra-revenue)","REVENUE"),
    ("MAINTENANCE_EXPENSE","Property maintenance","EXPENSE"),
    ("UTILITY_EXPENSE","Utilities paid","EXPENSE"),
    ("MANAGEMENT_FEES","Management expenses","EXPENSE"),
    ("INSURANCE_EXPENSE","Property insurance","EXPENSE"),
    ("PROPERTY_TAX_EXPENSE","Property taxation","EXPENSE"),
    ("OTHER_EXPENSE","Other approved operating expenses","EXPENSE"),
)

def upgrade():
    op.create_table("gl_accounts",
        sa.Column("code",sa.String(40),primary_key=True),
        sa.Column("name",sa.String(180),nullable=False),
        sa.Column("kind",sa.String(15),nullable=False),
        sa.Column("active",sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.CheckConstraint("kind IN ('ASSET','LIABILITY','EQUITY','REVENUE','EXPENSE')",name="ck_gl_account_kind"))
    op.bulk_insert(
        sa.table("gl_accounts", sa.column("code",sa.String()),
                 sa.column("name",sa.String()),sa.column("kind",sa.String())),
        [{"code":c,"name":n,"kind":k} for c,n,k in COA])
    op.create_table("gl_events",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("event_key",sa.String(160),nullable=False,unique=True),
        sa.Column("kind",sa.String(40),nullable=False),
        sa.Column("posted_on",sa.Date(),nullable=False),
        sa.Column("property_id",sa.String(36),sa.ForeignKey("properties.id",ondelete="RESTRICT")),
        sa.Column("actor_id",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT")),
        sa.Column("fingerprint",sa.String(64),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_gl_events_posted_on","gl_events",["posted_on"])
    op.create_index("ix_gl_events_property_id","gl_events",["property_id"])
    op.create_table("gl_lines",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("event_id",sa.String(36),sa.ForeignKey("gl_events.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("account_code",sa.String(40),sa.ForeignKey("gl_accounts.code",ondelete="RESTRICT"),nullable=False),
        sa.Column("debit_ugx",sa.BigInteger(),nullable=False),
        sa.Column("credit_ugx",sa.BigInteger(),nullable=False),
        sa.CheckConstraint("debit_ugx >= 0 AND credit_ugx >= 0",name="ck_gl_nonnegative"),
        sa.CheckConstraint("(debit_ugx > 0 AND credit_ugx = 0) OR (credit_ugx > 0 AND debit_ugx = 0)",name="ck_gl_one_sided_line"))
    op.create_index("ix_gl_lines_event_id","gl_lines",["event_id"])
    op.create_index("ix_gl_lines_account_code","gl_lines",["account_code"])
    op.create_table("gl_period_closures",
        sa.Column("period",sa.String(7),primary_key=True),
        sa.Column("closed_by",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("closed_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("gl_opening_batches",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("import_sha256",sa.String(64),nullable=False,unique=True),
        sa.Column("effective_on",sa.Date(),nullable=False),
        sa.Column("rows",sa.JSON(),nullable=False),
        sa.Column("note",sa.String(500),nullable=False),
        sa.Column("status",sa.String(15),nullable=False),
        sa.Column("submitted_by",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("approved_by",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT")),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("approved_at",sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('PENDING','POSTED','REJECTED')",name="ck_gl_opening_status"))
    if op.get_bind().dialect.name=="postgresql":
        for table in ("gl_events","gl_lines","gl_period_closures"):
            op.execute(f"CREATE TRIGGER kats_immutable_{table} BEFORE UPDATE OR DELETE ON {table} "
                       "FOR EACH ROW EXECUTE FUNCTION kats_append_only_guard()")
        # DEFERRABLE: account lines may be staged after the event flush, but
        # every committed event must have >=2 balanced nonzero lines.
        op.execute("""
            CREATE FUNCTION kats_validate_gl_event() RETURNS trigger
            LANGUAGE plpgsql AS $gl_balanced$
            DECLARE target_id text; amount_dr bigint; amount_cr bigint; line_count integer;
            BEGIN
              IF TG_TABLE_NAME = 'gl_events' THEN
                target_id := NEW.id;
              ELSE
                target_id := NEW.event_id;
              END IF;
              SELECT count(*),coalesce(sum(debit_ugx),0),coalesce(sum(credit_ugx),0)
                INTO line_count,amount_dr,amount_cr FROM gl_lines WHERE event_id=target_id;
              IF line_count < 2 OR amount_dr <> amount_cr OR amount_dr <= 0 THEN
                RAISE EXCEPTION USING MESSAGE='Unbalanced general ledger event '||target_id;
              END IF;
              RETURN NEW;
            END
            $gl_balanced$;
        """)
        for table in ("gl_events","gl_lines"):
            op.execute(f"CREATE CONSTRAINT TRIGGER kats_balanced_{table} "
                       f"AFTER INSERT ON {table} DEFERRABLE INITIALLY DEFERRED "
                       "FOR EACH ROW EXECUTE FUNCTION kats_validate_gl_event()")

def downgrade():
    if op.get_bind().dialect.name=="postgresql":
        for table in ("gl_lines","gl_events"):
            op.execute(f"DROP TRIGGER IF EXISTS kats_balanced_{table} ON {table}")
        for table in ("gl_lines","gl_events","gl_period_closures"):
            op.execute(f"DROP TRIGGER IF EXISTS kats_immutable_{table} ON {table}")
        op.execute("DROP FUNCTION IF EXISTS kats_validate_gl_event()")
    op.drop_table("gl_opening_batches")
    op.drop_table("gl_period_closures")
    op.drop_index("ix_gl_lines_account_code",table_name="gl_lines")
    op.drop_index("ix_gl_lines_event_id",table_name="gl_lines")
    op.drop_table("gl_lines")
    op.drop_index("ix_gl_events_property_id",table_name="gl_events")
    op.drop_index("ix_gl_events_posted_on",table_name="gl_events")
    op.drop_table("gl_events")
    op.drop_table("gl_accounts")
