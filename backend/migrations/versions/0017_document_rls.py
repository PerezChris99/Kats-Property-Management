"""Force database-level row access policies for private documents.

Tenant/doc access is independently rechecked by Postgres using SET LOCAL
scope derived from authenticated user. Admin/worker operations outside this
scope require explicitly privileged database roles and an audited procedure.
"""
from alembic import op

revision="0017_document_rls"
down_revision="0016_query_indexes"
branch_labels=None
depends_on=None

_POLICY = """
CREATE POLICY kats_document_scope ON documents
FOR ALL
USING (
    current_setting('kats.actor_role', true) IN
      ('SUPER_ADMIN','OWNER','MANAGER','ACCOUNTANT')
    OR (
      current_setting('kats.actor_role', true) = 'TENANT'
      AND tenant_id = NULLIF(current_setting('kats.actor_tenant_id', true), '')
    )
    OR (
      current_setting('kats.actor_role', true) = 'CARETAKER'
      AND category IN ('ROOM_PHOTO','INSPECTION')
      AND room_id IS NOT NULL
      AND EXISTS (
        SELECT 1 FROM caretaker_assignments assignment
        WHERE assignment.room_id = documents.room_id
          AND assignment.caretaker_user_id =
             current_setting('kats.actor_user_id', true)
      )
    )
)
WITH CHECK (
    current_setting('kats.actor_role', true) IN
      ('SUPER_ADMIN','OWNER','MANAGER','ACCOUNTANT')
    OR (
      current_setting('kats.actor_role', true) = 'TENANT'
      AND tenant_id = NULLIF(current_setting('kats.actor_tenant_id', true), '')
      AND category IN ('PAYMENT_PROOF','INSPECTION','LEASE')
    )
    OR (
      current_setting('kats.actor_role', true) = 'CARETAKER'
      AND category IN ('ROOM_PHOTO','INSPECTION')
      AND room_id IS NOT NULL
      AND EXISTS (
        SELECT 1 FROM caretaker_assignments assignment
        WHERE assignment.room_id = documents.room_id
          AND assignment.caretaker_user_id =
             current_setting('kats.actor_user_id', true)
      )
    )
)
"""

def upgrade():
    if op.get_bind().dialect.name=="postgresql":
        op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY")
        op.execute(_POLICY)
        op.execute("ALTER TABLE documents FORCE ROW LEVEL SECURITY")

def downgrade():
    if op.get_bind().dialect.name=="postgresql":
        op.execute("DROP POLICY IF EXISTS kats_document_scope ON documents")
        op.execute("ALTER TABLE documents NO FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE documents DISABLE ROW LEVEL SECURITY")
