"""Keep new property records mapped to the existing business.

Revision ID: 0030_legacy_property_mapping
Revises: 0029_receipt_journal

This is an interim, single-business invariant. Do not enable independent
organization onboarding before replacing it with authenticated org scoping.
"""
from alembic import op

revision="0030_legacy_property_mapping"
down_revision="0029_receipt_journal"
branch_labels=None
depends_on=None

def upgrade():
    if op.get_bind().dialect.name!="postgresql":
        return
    op.execute("""
    CREATE FUNCTION kats_map_legacy_property() RETURNS trigger
    LANGUAGE plpgsql AS $kats_property$
    BEGIN
      INSERT INTO property_organizations (property_id,organization_id,created_at)
      VALUES (NEW.id,'11111111-1111-4111-8111-111111111111',NOW());
      RETURN NEW;
    END;
    $kats_property$;
    """)
    op.execute("""
    CREATE TRIGGER kats_map_legacy_property_insert
    AFTER INSERT ON properties
    FOR EACH ROW EXECUTE FUNCTION kats_map_legacy_property()
    """)

def downgrade():
    if op.get_bind().dialect.name!="postgresql":
        return
    op.execute("DROP TRIGGER IF EXISTS kats_map_legacy_property_insert ON properties")
    op.execute("DROP FUNCTION IF EXISTS kats_map_legacy_property()")
