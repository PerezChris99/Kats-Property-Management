"""Preventive maintenance schedule and durable occurrence keys."""
from alembic import op
import sqlalchemy as sa
revision="0025_preventive_maintenance"
down_revision="0024_tenancy_disputes"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("maintenance_plans",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("room_id",sa.String(36),sa.ForeignKey("rooms.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("title",sa.String(120),nullable=False),
        sa.Column("instructions",sa.Text,nullable=False),
        sa.Column("priority",sa.String(20),nullable=False),
        sa.Column("cadence_days",sa.Integer,nullable=False),
        sa.Column("next_due_on",sa.Date,nullable=False),
        sa.Column("status",sa.String(20),nullable=False),
        sa.Column("created_by",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("cadence_days BETWEEN 1 AND 366",name="ck_maintenance_plan_cadence"),
        sa.CheckConstraint("priority IN ('LOW','MEDIUM','HIGH','URGENT')",name="ck_maintenance_plan_priority"),
        sa.CheckConstraint("status IN ('ACTIVE','PAUSED','RETIRED')",name="ck_maintenance_plan_status"))
    op.create_index("ix_maintenance_plans_room_id","maintenance_plans",["room_id"])
    op.create_index("ix_maintenance_plans_next_due_on","maintenance_plans",["next_due_on"])
    op.create_index("ix_maintenance_plans_due_status","maintenance_plans",["status","next_due_on"])
    op.create_table("maintenance_occurrences",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("plan_id",sa.String(36),sa.ForeignKey("maintenance_plans.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("scheduled_for",sa.Date,nullable=False),
        sa.Column("maintenance_request_id",sa.String(36),sa.ForeignKey("maintenance_requests.id",ondelete="RESTRICT"),nullable=False,unique=True),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("plan_id","scheduled_for",name="uq_maintenance_plan_occurrence"))
    op.create_index("ix_maintenance_occurrences_plan_id","maintenance_occurrences",["plan_id"])

def downgrade():
    op.drop_index("ix_maintenance_occurrences_plan_id",table_name="maintenance_occurrences")
    op.drop_table("maintenance_occurrences")
    op.drop_index("ix_maintenance_plans_due_status",table_name="maintenance_plans")
    op.drop_index("ix_maintenance_plans_next_due_on",table_name="maintenance_plans")
    op.drop_index("ix_maintenance_plans_room_id",table_name="maintenance_plans")
    op.drop_table("maintenance_plans")
