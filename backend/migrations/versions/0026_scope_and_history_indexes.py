"""Tenant-scoped PostgreSQL RLS and high-traffic history indexes.

Scope applies to the runtime database role even when it owns the tables
(FORCE RLS). All policies default-deny absent a verified per-transaction
application scope. A separately provisioned restricted, non-BYPASSRLS
runtime SQL role is mandatory for real isolation.
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_scope_and_history_indexes"
down_revision = "0025_preventive_maintenance"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_invoices_history_seek", "invoices", ("created_at", "id")),
    ("ix_invoices_tenant_history_seek", "invoices", ("tenant_id", "created_at", "id")),
    ("ix_payments_history_seek", "payments", ("created_at", "id")),
    ("ix_maintenance_history_seek", "maintenance_requests", ("created_at", "id")),
    ("ix_audit_history_seek", "audit_logs", ("created_at", "id")),
    ("ix_lease_tenant_active", "leases", ("tenant_id", "status", "end_date")),
    ("ix_payments_invoice_history_seek", "payments", ("invoice_id", "created_at", "id")),
    ("ix_notifications_user_history_seek", "notifications", ("user_id", "created_at", "id")),
    ("ix_maintenance_room_status", "maintenance_requests", ("room_id", "status")),
    ("ix_caretaker_room_user_lookup", "caretaker_assignments", ("room_id", "caretaker_user_id")),
    ("ix_audit_target_history_seek", "audit_logs", ("target_type", "target_id", "created_at")),
)

# Session context is set only from a valid, non-revoked JWT or inside a
# trusted Celery worker task, with set_config(..., true) (transaction-local).
ROLE = "current_setting('kats.actor_role', true)"
ACTOR = "NULLIF(current_setting('kats.actor_user_id', true), '')"
TENANT = "NULLIF(current_setting('kats.actor_tenant_id', true), '')"
STAFF = f"{ROLE} IN ('OWNER','MANAGER','ACCOUNTANT','SUPER_ADMIN','SERVICE')"
TENANT_SELF = f"{ROLE} = 'TENANT' AND tenant_id = {TENANT}"
ASSIGNED_ROOM = (f"{ROLE} = 'CARETAKER' AND EXISTS ("
                 f"SELECT 1 FROM caretaker_assignments a "
                 f"WHERE a.room_id = room_id AND a.caretaker_user_id = {ACTOR})")
LEASE_ASSIGNED = (f"{ROLE} = 'CARETAKER' AND EXISTS ("
                  f"SELECT 1 FROM caretaker_assignments a "
                  f"WHERE a.room_id = leases.room_id AND a.caretaker_user_id = {ACTOR})")
INV_ASSIGNED = (f"{ROLE} = 'CARETAKER' AND EXISTS ("
                f"SELECT 1 FROM leases l JOIN caretaker_assignments a ON a.room_id=l.room_id "
                f"WHERE l.id = invoices.lease_id AND a.caretaker_user_id = {ACTOR})")
PAYMENT_OWN_INVOICE = (
    f"EXISTS (SELECT 1 FROM invoices i WHERE i.id = payments.invoice_id "
    f"AND i.tenant_id = {TENANT})"
)
PAYMENT_ASSIGNED_INVOICE = (
    f"EXISTS (SELECT 1 FROM invoices i "
    f"JOIN leases l ON l.id=i.lease_id "
    f"JOIN caretaker_assignments a ON a.room_id=l.room_id "
    f"WHERE i.id=payments.invoice_id AND a.caretaker_user_id={ACTOR})"
)
# These expressions use only fixed SQL authored here, never interpolated input.
POLICIES = (
    ("tenants",
     f"({STAFF}) OR ({ROLE}='TENANT' AND user_id={ACTOR})",
     f"({STAFF})"),
    ("leases",
     f"({STAFF}) OR ({TENANT_SELF}) OR ({LEASE_ASSIGNED})",
     f"({STAFF})"),
    ("invoices",
     f"({STAFF}) OR ({TENANT_SELF}) OR ({INV_ASSIGNED})",
     f"({STAFF})"),
    ("payments",
     f"({STAFF}) OR ({ROLE}='TENANT' AND {PAYMENT_OWN_INVOICE}) "
     f"OR ({ROLE}='CARETAKER' AND {PAYMENT_ASSIGNED_INVOICE})",
     f"({STAFF}) OR "
     f"({ROLE}='TENANT' AND created_by={ACTOR} AND {PAYMENT_OWN_INVOICE}) "
     f"OR ({ROLE}='CARETAKER' AND created_by={ACTOR} AND {PAYMENT_ASSIGNED_INVOICE})"),
    ("maintenance_requests",
     f"({STAFF}) OR ({TENANT_SELF}) OR "
     f"({ROLE}='CARETAKER' AND EXISTS (SELECT 1 FROM caretaker_assignments a "
     f"WHERE a.room_id=maintenance_requests.room_id AND a.caretaker_user_id={ACTOR}))",
     f"({STAFF}) OR "
     f"({ROLE}='TENANT' AND tenant_id={TENANT} AND EXISTS ("
     f"SELECT 1 FROM leases l WHERE l.tenant_id={TENANT} "
     f"AND l.room_id=maintenance_requests.room_id AND l.status='ACTIVE')) "
     f"OR ({ROLE}='CARETAKER' AND EXISTS (SELECT 1 FROM caretaker_assignments a "
     f"WHERE a.room_id=maintenance_requests.room_id AND a.caretaker_user_id={ACTOR}))"),
    ("notifications",
     f"({ROLE}='SERVICE') OR (user_id={ACTOR})",
     f"({ROLE}='SERVICE') OR (user_id={ACTOR})"),
)


def upgrade():
    for name, table, columns in INDEXES:
        op.create_index(name, table, list(columns))
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, using, check in POLICIES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY kats_runtime_scope ON {table} "
                   f"FOR ALL USING ({using}) WITH CHECK ({check})")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table, _using, _check in reversed(POLICIES):
            op.execute(f"DROP POLICY IF EXISTS kats_runtime_scope ON {table}")
            op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for name, table, _cols in reversed(INDEXES):
        op.drop_index(name, table_name=table)
