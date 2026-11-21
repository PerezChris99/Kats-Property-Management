"""Hold approved advance rent separately from invoice receivables."""
from alembic import op
import sqlalchemy as sa

revision = "0038_rent_advances"
down_revision = "0037_bank_books"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("rent_advances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lease_id", sa.String(36), sa.ForeignKey("leases.id"), nullable=False),
        sa.Column("amount_ugx", sa.BigInteger(), nullable=False),
        sa.Column("method", sa.String(25), nullable=False),
        sa.Column("reference", sa.String(160), unique=True, nullable=False),
        sa.Column("idempotency_key", sa.String(128), unique=True, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("amount_ugx > 0", name="ck_advance_positive"),
        sa.CheckConstraint("status IN ('PENDING','APPROVED','REVERSED')", name="ck_advance_state"))
    op.create_index("ix_rent_advances_lease_id", "rent_advances", ["lease_id"])
    with op.batch_alter_table("payments") as batch:
        batch.add_column(sa.Column("advance_id", sa.String(36)))
        batch.create_foreign_key("fk_payment_advance", "rent_advances", ["advance_id"], ["id"])
        batch.create_index("ix_payments_advance_id", ["advance_id"])
    op.execute("""INSERT INTO gl_accounts(code,name,kind,active) VALUES
               ('TENANT_ADVANCES','Rent received before invoice allocation','LIABILITY',true)
               ON CONFLICT(code) DO NOTHING""")
    if op.get_bind().dialect.name == "postgresql":
        staff = "current_setting('kats.actor_role',true) IN ('OWNER','ACCOUNTANT','MANAGER','SUPER_ADMIN')"
        op.execute("ALTER TABLE rent_advances ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE rent_advances FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY advance_staff ON rent_advances FOR ALL USING ({staff}) WITH CHECK ({staff})")
        op.execute("""CREATE POLICY advance_tenant ON rent_advances FOR SELECT USING (
            current_setting('kats.actor_role',true) = 'TENANT' AND EXISTS (
                SELECT 1 FROM leases WHERE leases.id=rent_advances.lease_id AND
                leases.tenant_id=current_setting('kats.actor_tenant_id',true)))""")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("LOCK TABLE rent_advances IN ACCESS EXCLUSIVE MODE")
        op.execute("ALTER TABLE rent_advances DISABLE ROW LEVEL SECURITY")
    if op.get_bind().execute(sa.text("SELECT count(*) FROM rent_advances")).scalar():
        raise RuntimeError("Restore a verified backup to roll back a database containing rent advances")
    op.execute("DELETE FROM gl_accounts WHERE code='TENANT_ADVANCES'")
    with op.batch_alter_table("payments") as batch:
        batch.drop_index("ix_payments_advance_id")
        batch.drop_constraint("fk_payment_advance", type_="foreignkey")
        batch.drop_column("advance_id")
    op.drop_table("rent_advances")
