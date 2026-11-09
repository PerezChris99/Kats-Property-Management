"""Caretaker room assignments"""
from alembic import op
import sqlalchemy as sa

revision = "0002_caretakers"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "caretaker_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("caretaker_user_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("room_id", sa.String(36),
                  sa.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("caretaker_user_id", "room_id", name="uq_caretaker_assigned_room")
    )
    op.create_index("ix_caretaker_assignments_caretaker_user_id", "caretaker_assignments", ["caretaker_user_id"])
    op.create_index("ix_caretaker_assignments_room_id", "caretaker_assignments", ["room_id"])

def downgrade():
    op.drop_table("caretaker_assignments")
