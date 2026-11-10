"""Tenant dispute register and non-destructive event history."""
from alembic import op
import sqlalchemy as sa
revision="0024_tenancy_disputes"
down_revision="0023_privacy_requests"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("tenancy_disputes",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("lease_id",sa.String(36),sa.ForeignKey("leases.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("tenant_id",sa.String(36),sa.ForeignKey("tenants.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("kind",sa.String(24),nullable=False),
        sa.Column("title",sa.String(160),nullable=False),
        sa.Column("description",sa.Text,nullable=False),
        sa.Column("status",sa.String(24),nullable=False),
        sa.Column("opened_by",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("reviewed_by",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT")),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("closed_at",sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind IN ('RENT','DEPOSIT','REPAIR','SERVICE','NOTICE','OTHER')",name="ck_dispute_kind"),
        sa.CheckConstraint("status IN ('OPEN','IN_REVIEW','RESOLVED','DECLINED')",name="ck_dispute_status"))
    op.create_index("ix_tenancy_disputes_lease_id","tenancy_disputes",["lease_id"])
    op.create_index("ix_tenancy_disputes_tenant_id","tenancy_disputes",["tenant_id"])
    op.create_index("ix_tenancy_disputes_created_at","tenancy_disputes",["created_at"])
    op.create_index("ix_tenancy_disputes_status_created","tenancy_disputes",["status","created_at"])
    op.create_table("dispute_events",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("dispute_id",sa.String(36),sa.ForeignKey("tenancy_disputes.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("actor_id",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("event",sa.String(32),nullable=False),
        sa.Column("comment",sa.Text,nullable=False),
        sa.Column("previous_status",sa.String(24)),
        sa.Column("new_status",sa.String(24)),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_dispute_events_dispute_id","dispute_events",["dispute_id"])
    op.create_index("ix_dispute_events_created_at","dispute_events",["created_at"])

def downgrade():
    op.drop_index("ix_dispute_events_created_at",table_name="dispute_events")
    op.drop_index("ix_dispute_events_dispute_id",table_name="dispute_events")
    op.drop_table("dispute_events")
    op.drop_index("ix_tenancy_disputes_status_created",table_name="tenancy_disputes")
    op.drop_index("ix_tenancy_disputes_created_at",table_name="tenancy_disputes")
    op.drop_index("ix_tenancy_disputes_tenant_id",table_name="tenancy_disputes")
    op.drop_index("ix_tenancy_disputes_lease_id",table_name="tenancy_disputes")
    op.drop_table("tenancy_disputes")
