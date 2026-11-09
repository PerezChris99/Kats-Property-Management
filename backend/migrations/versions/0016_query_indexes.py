"""Composite workload indexes for bounded, targeted API list queries.

Review table size and use an online CONCURRENTLY strategy on already-large
production tables before applying this standard transactional migration.
"""
from alembic import op

revision = "0016_query_indexes"
down_revision = "0015_settlement_dates"
branch_labels = None
depends_on = None

INDEXES = [["rooms","ix_rooms_property_status",["property_id","status"]],["leases","ix_leases_status_end",["status","end_date"]],["invoices","ix_invoices_tenant_due",["tenant_id","due_date"]],["invoices","ix_invoices_status_due",["status","due_date"]],["payments","ix_payments_invoice_status",["invoice_id","status"]],["payments","ix_payments_creator_status",["created_by","status"]],["maintenance_requests","ix_maintenance_status_created",["status","created_at"]],["maintenance_requests","ix_maintenance_tenant_created",["tenant_id","created_at"]],["expenses","ix_expenses_status_incurred",["status","incurred_on"]],["audit_logs","ix_audit_actor_created",["actor_id","created_at"]],["inspections","ix_inspections_lease_kind",["lease_id","kind"]],["deposit_movements","ix_deposits_lease_status",["lease_id","status"]],["documents","ix_documents_tenant_created",["tenant_id","created_at"]],["notifications","ix_notifications_user_created",["user_id","created_at"]]]

def upgrade():
    for table, name, columns in INDEXES:
        op.create_index(name, table, columns)

def downgrade():
    for table, name, _columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)
