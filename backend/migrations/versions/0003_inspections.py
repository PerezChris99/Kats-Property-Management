"""Inspections for lease move-in/move-out lifecycle."""
from alembic import op
import sqlalchemy as sa

revision = "0003_inspections"
down_revision = "0002_caretakers"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "inspections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lease_id", sa.String(36),
                  sa.ForeignKey("leases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("room_id", sa.String(36),
                  sa.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("inspector_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("condition_notes", sa.Text(), nullable=False),
        sa.Column("damage_estimate_ugx", sa.BigInteger(), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("damage_estimate_ugx >= 0", name="ck_inspection_damage"),
        sa.CheckConstraint("kind IN ('MOVE_IN','MOVE_OUT','ROUTINE')",
                           name="ck_inspection_kind"),
    )
    op.create_index("ix_inspections_lease_id", "inspections", ["lease_id"])
    op.create_index("ix_inspections_room_id", "inspections", ["room_id"])

def downgrade():
    op.drop_table("inspections")
