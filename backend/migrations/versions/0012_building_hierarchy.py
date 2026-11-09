"""Property building and floor hierarchy; preserve unassigned legacy rooms."""
from alembic import op
import sqlalchemy as sa
revision="0012_building_hierarchy"
down_revision="0011_contact"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("buildings",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("property_id",sa.String(36),sa.ForeignKey("properties.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("name",sa.String(160),nullable=False),
        sa.Column("description",sa.String(500)),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("property_id","name",name="uq_property_building_name"))
    op.create_index("ix_buildings_property_id","buildings",["property_id"])
    op.create_table("floors",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("building_id",sa.String(36),sa.ForeignKey("buildings.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("level",sa.Integer(),nullable=False),
        sa.Column("label",sa.String(100),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("building_id","level",name="uq_building_floor_level"),
        sa.CheckConstraint("level BETWEEN -10 AND 300",name="ck_floor_level"))
    op.create_index("ix_floors_building_id","floors",["building_id"])
    op.add_column("rooms",sa.Column("floor_id",sa.String(36),sa.ForeignKey("floors.id",ondelete="RESTRICT"),nullable=True))
    op.create_index("ix_rooms_floor_id","rooms",["floor_id"])

def downgrade():
    op.drop_index("ix_rooms_floor_id",table_name="rooms")
    op.drop_column("rooms","floor_id")
    op.drop_table("floors")
    op.drop_table("buildings")
