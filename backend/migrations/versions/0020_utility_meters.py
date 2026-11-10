"""Tracked water/electricity meter readings and one-time invoice allocation."""
from alembic import op
import sqlalchemy as sa
revision="0020_utility_meters"
down_revision="0019_tenancy_notices"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("utility_meters",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("room_id",sa.String(36),sa.ForeignKey("rooms.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("kind",sa.String(20),nullable=False),
        sa.Column("tariff_ugx_per_unit",sa.BigInteger,nullable=False),
        sa.Column("baseline_milli_units",sa.BigInteger,nullable=False),
        sa.Column("created_by",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("room_id","kind",name="uq_meter_room_kind"),
        sa.CheckConstraint("tariff_ugx_per_unit > 0 AND baseline_milli_units >= 0",name="ck_meter_tariff"),
        sa.CheckConstraint("kind IN ('WATER','ELECTRICITY')",name="ck_meter_kind"))
    op.create_index("ix_utility_meters_room_id","utility_meters",["room_id"])
    op.create_table("utility_readings",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("meter_id",sa.String(36),sa.ForeignKey("utility_meters.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("previous_milli_units",sa.BigInteger,nullable=False),
        sa.Column("current_milli_units",sa.BigInteger,nullable=False),
        sa.Column("used_milli_units",sa.BigInteger,nullable=False),
        sa.Column("tariff_ugx_per_unit",sa.BigInteger,nullable=False),
        sa.Column("charge_ugx",sa.BigInteger,nullable=False),
        sa.Column("observed_on",sa.Date,nullable=False),
        sa.Column("idempotency_key",sa.String(128),nullable=False,unique=True),
        sa.Column("invoice_line_id",sa.String(36),sa.ForeignKey("invoice_lines.id",ondelete="RESTRICT"),unique=True),
        sa.Column("recorded_by",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("current_milli_units >= previous_milli_units AND previous_milli_units >= 0",name="ck_utility_reading_monotonic"),
        sa.CheckConstraint("used_milli_units = current_milli_units - previous_milli_units",name="ck_utility_consumption"),
        sa.CheckConstraint("charge_ugx >= 0 AND tariff_ugx_per_unit > 0",name="ck_utility_charge"))
    op.create_index("ix_utility_readings_meter_id","utility_readings",["meter_id"])
    op.create_index("ix_utility_readings_meter_date","utility_readings",["meter_id","observed_on"])

def downgrade():
    op.drop_index("ix_utility_readings_meter_date",table_name="utility_readings")
    op.drop_index("ix_utility_readings_meter_id",table_name="utility_readings")
    op.drop_table("utility_readings")
    op.drop_index("ix_utility_meters_room_id",table_name="utility_meters")
    op.drop_table("utility_meters")
