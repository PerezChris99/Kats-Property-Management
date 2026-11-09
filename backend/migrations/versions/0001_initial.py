"""Initial schema (2026-11-09). Keep this revision independent of later model edits."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def ident():
    return sa.Column("id", sa.String(36), primary_key=True)

def stamped():
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)

def fk(column, target, optional=False, ondelete="RESTRICT"):
    return sa.Column(column, sa.String(36), sa.ForeignKey(target, ondelete=ondelete), nullable=optional)

def upgrade():
    op.create_table("users", ident(), sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False), stamped())
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table("properties", ident(), sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.String(400), nullable=False),
        sa.Column("district", sa.String(120), nullable=False), stamped())
    op.create_table("rooms", ident(), fk("property_id", "properties.id"),
        sa.Column("number", sa.String(60), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("rent_ugx", sa.BigInteger(), nullable=False),
        sa.Column("deposit_ugx", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("property_id", "number", name="uq_property_room"),
        sa.CheckConstraint("rent_ugx >= 0 AND deposit_ugx >= 0", name="ck_room_amounts"))
    op.create_index("ix_rooms_property_id", "rooms", ["property_id"])
    op.create_table("room_state_history", ident(), fk("room_id", "rooms.id"),
        sa.Column("old_status", sa.String(30), nullable=False),
        sa.Column("new_status", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        fk("actor_id", "users.id"), stamped())
    op.create_index("ix_room_state_history_room_id", "room_state_history", ["room_id"])
    op.create_table("tenants", ident(),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), unique=True),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("email", sa.String(254)), stamped())
    op.create_table("leases", ident(), fk("tenant_id", "tenants.id"), fk("room_id", "rooms.id"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("rent_ugx", sa.BigInteger(), nullable=False),
        sa.Column("deposit_ugx", sa.BigInteger(), nullable=False),
        sa.Column("due_day", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.CheckConstraint("end_date > start_date", name="ck_lease_dates"),
        sa.CheckConstraint("rent_ugx >= 0 AND deposit_ugx >= 0 AND due_day BETWEEN 1 AND 28", name="ck_lease_terms"))
    op.create_index("ix_leases_tenant_id", "leases", ["tenant_id"])
    op.create_index("ix_leases_room_id", "leases", ["room_id"])
    op.create_index("uq_active_lease_per_room", "leases", ["room_id"], unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"), sqlite_where=sa.text("status = 'ACTIVE'"))
    op.create_table("invoices", ident(),
        sa.Column("invoice_number", sa.String(70), nullable=False, unique=True),
        fk("lease_id", "leases.id"), fk("tenant_id", "tenants.id"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("total_ugx", sa.BigInteger(), nullable=False),
        sa.Column("paid_ugx", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False), stamped(),
        sa.UniqueConstraint("lease_id", "period_start", "period_end", name="uq_lease_billing_period"),
        sa.CheckConstraint("total_ugx >= 0 AND paid_ugx >= 0 AND paid_ugx <= total_ugx", name="ck_invoice_amounts"),
        sa.CheckConstraint("period_end >= period_start", name="ck_invoice_period"))
    op.create_index("ix_invoices_lease_id", "invoices", ["lease_id"])
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])
    op.create_table("payments", ident(), fk("invoice_id", "invoices.id"),
        sa.Column("amount_ugx", sa.BigInteger(), nullable=False),
        sa.Column("method", sa.String(25), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("reference", sa.String(160), unique=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        fk("created_by", "users.id"), fk("reviewed_by", "users.id", optional=True), stamped(),
        sa.CheckConstraint("amount_ugx > 0", name="ck_payment_positive"))
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])
    op.create_table("ledger_entries", ident(), fk("invoice_id", "invoices.id"),
        fk("payment_id", "payments.id", optional=True),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("amount_ugx", sa.BigInteger(), nullable=False), stamped())
    op.create_index("ix_ledger_entries_invoice_id", "ledger_entries", ["invoice_id"])
    op.create_table("maintenance_requests", ident(), fk("room_id", "rooms.id"),
        fk("tenant_id", "tenants.id", optional=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False), stamped())
    op.create_index("ix_maintenance_requests_room_id", "maintenance_requests", ["room_id"])
    op.create_table("expenses", ident(), fk("property_id", "properties.id"),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount_ugx", sa.BigInteger(), nullable=False),
        sa.Column("incurred_on", sa.Date(), nullable=False), fk("created_by", "users.id"),
        sa.CheckConstraint("amount_ugx >= 0", name="ck_expense_nonnegative"))
    op.create_index("ix_expenses_property_id", "expenses", ["property_id"])
    op.create_table("audit_logs", ident(), fk("actor_id", "users.id"),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(60), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False), stamped())
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

def downgrade():
    for name in ("audit_logs", "expenses", "maintenance_requests", "ledger_entries",
                 "payments", "invoices", "leases", "tenants", "room_state_history",
                 "rooms", "properties", "users"):
        op.drop_table(name)
