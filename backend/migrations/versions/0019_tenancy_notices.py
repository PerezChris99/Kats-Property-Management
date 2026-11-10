"""Tenant notice service records and effective-dated rent increase audit."""
from alembic import op
import sqlalchemy as sa
revision="0019_tenancy_notices"
down_revision="0018_ephemeral_retention"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("tenancy_notices",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("lease_id",sa.String(36),sa.ForeignKey("leases.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("notice_type",sa.String(30),nullable=False),
        sa.Column("proposed_rent_ugx",sa.BigInteger),
        sa.Column("served_on",sa.Date,nullable=False),
        sa.Column("effective_on",sa.Date,nullable=False),
        sa.Column("delivery_method",sa.String(30),nullable=False),
        sa.Column("delivery_reference",sa.String(300),nullable=False),
        sa.Column("reason",sa.String(500),nullable=False),
        sa.Column("served_by",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("effective_on >= served_on",name="ck_notice_dates"),
        sa.CheckConstraint("proposed_rent_ugx IS NULL OR proposed_rent_ugx > 0",name="ck_notice_rent"))
    op.create_index("ix_tenancy_notices_lease_id","tenancy_notices",["lease_id"])
    op.create_index("ix_tenancy_notices_created_at","tenancy_notices",["created_at"])
    op.add_column("lease_amendments",sa.Column("rent_notice_id",sa.String(36),nullable=True))
    op.create_foreign_key("fk_amendment_notice","lease_amendments","tenancy_notices",["rent_notice_id"],["id"],ondelete="RESTRICT")

def downgrade():
    op.drop_constraint("fk_amendment_notice","lease_amendments",type_="foreignkey")
    op.drop_column("lease_amendments","rent_notice_id")
    op.drop_index("ix_tenancy_notices_created_at",table_name="tenancy_notices")
    op.drop_index("ix_tenancy_notices_lease_id",table_name="tenancy_notices")
    op.drop_table("tenancy_notices")
