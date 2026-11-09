"""Lease renewal history and approved deposit movement tracking."""
from alembic import op
import sqlalchemy as sa
revision = "0007_lease_deposits"
down_revision = "0006_operations"
branch_labels = None
depends_on = None
def fk(name,target,nullable=False):
    return sa.Column(name,sa.String(36),sa.ForeignKey(target,ondelete="RESTRICT"),nullable=nullable)
def idc():
    return sa.Column("id",sa.String(36),primary_key=True)
def dt(name,nullable=False):
    return sa.Column(name,sa.DateTime(timezone=True),nullable=nullable)

def upgrade():
    op.create_table("lease_amendments",idc(),fk("lease_id","leases.id"),
        sa.Column("previous_end_date",sa.Date(),nullable=False),
        sa.Column("new_end_date",sa.Date(),nullable=False),
        sa.Column("effective_date",sa.Date(),nullable=False),
        sa.Column("previous_rent_ugx",sa.BigInteger(),nullable=False),
        sa.Column("new_rent_ugx",sa.BigInteger(),nullable=False),
        sa.Column("reason",sa.String(500),nullable=False),
        fk("created_by","users.id"),dt("created_at"),
        sa.CheckConstraint("new_end_date > previous_end_date",name="ck_renewal_dates"),
        sa.CheckConstraint("previous_rent_ugx > 0 AND new_rent_ugx > 0",name="ck_renewal_rent"))
    op.create_index("ix_lease_amendments_lease_id","lease_amendments",["lease_id"])
    op.create_table("deposit_movements",idc(),fk("lease_id","leases.id"),
        sa.Column("kind",sa.String(20),nullable=False),
        sa.Column("amount_ugx",sa.BigInteger(),nullable=False),
        sa.Column("external_reference",sa.String(160)),
        sa.Column("reason",sa.String(500),nullable=False),
        sa.Column("idempotency_key",sa.String(128),nullable=False,unique=True),
        sa.Column("status",sa.String(30),nullable=False),
        fk("created_by","users.id"),fk("reviewed_by","users.id",nullable=True),
        dt("created_at"),dt("reviewed_at",nullable=True),
        sa.CheckConstraint("amount_ugx > 0",name="ck_deposit_amount"),
        sa.CheckConstraint("kind IN ('HOLD','REFUND','WITHHOLD')",name="ck_deposit_kind"),
        sa.CheckConstraint("status IN ('PENDING_REVIEW','APPROVED','REJECTED')",name="ck_deposit_state"))
    op.create_index("ix_deposit_movements_lease_id","deposit_movements",["lease_id"])
def downgrade():
    op.drop_table("deposit_movements")
    op.drop_table("lease_amendments")
