"""Additive registry for later organization isolation; no tenant switching yet.

Revision ID: 0028_org_registry
Revises: 0027_maintenance_idempotency
"""
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa

revision = "0028_org_registry"
down_revision = "0027_maintenance_idempotency"
branch_labels = None
depends_on = None

LEGACY_ID = "11111111-1111-4111-8111-111111111111"


def upgrade():
    op.create_table(
        "organizations",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("slug",sa.String(100),nullable=False,unique=True),
        sa.Column("legal_name",sa.String(200),nullable=False),
        sa.Column("kind",sa.String(25),nullable=False),
        sa.Column("country_code",sa.String(2),nullable=False),
        sa.Column("status",sa.String(20),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("kind IN ('PROPERTY_OWNER','AGENCY','INSTITUTION')",name="ck_org_kind"),
        sa.CheckConstraint("status IN ('ACTIVE','SUSPENDED')",name="ck_org_status"),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id",ondelete="RESTRICT"),primary_key=True),
        sa.Column("user_id",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT"),primary_key=True),
        sa.Column("role",sa.String(30),nullable=False),
        sa.Column("active",sa.Boolean,nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
    )
    op.create_index("ix_org_memberships_user","organization_memberships",["user_id","active"])
    op.create_table(
        "property_organizations",
        sa.Column("property_id",sa.String(36),sa.ForeignKey("properties.id",ondelete="RESTRICT"),primary_key=True),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
    )
    op.create_index("ix_property_organizations_org","property_organizations",["organization_id"])
    connection = op.get_bind()
    current_time = datetime.now(timezone.utc)
    connection.execute(sa.text(
        "INSERT INTO organizations (id,slug,legal_name,kind,country_code,status,created_at) "
        "VALUES (:id,:slug,:name,:kind,:country,:status,:created)"
    ), {"id":LEGACY_ID, "slug":"kats-legacy", "name":"KATS Legacy Property Business",
        "kind":"PROPERTY_OWNER", "country":"UG", "status":"ACTIVE", "created":current_time})
    connection.execute(sa.text(
        "INSERT INTO property_organizations (property_id,organization_id,created_at) "
        "SELECT id,:org,:created FROM properties"
    ),{"org":LEGACY_ID,"created":current_time})
    connection.execute(sa.text(
        "INSERT INTO organization_memberships (organization_id,user_id,role,active,created_at) "
        "SELECT :org,id,role,:active,:created FROM users WHERE role <> 'SERVICE'"
    ),{"org":LEGACY_ID,"active":True,"created":current_time})


def downgrade():
    op.drop_index("ix_property_organizations_org",table_name="property_organizations")
    op.drop_table("property_organizations")
    op.drop_index("ix_org_memberships_user",table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
