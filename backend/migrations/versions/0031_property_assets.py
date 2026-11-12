"""Operational equipment inventory for the sole property business.

Revision ID: 0031_property_assets
Revises: 0030_legacy_property_mapping
"""
from alembic import op
import sqlalchemy as sa

revision="0031_property_assets"
down_revision="0030_legacy_property_mapping"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("property_assets",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("property_id",sa.String(36),sa.ForeignKey("properties.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("room_id",sa.String(36),sa.ForeignKey("rooms.id",ondelete="RESTRICT"),nullable=True),
        sa.Column("name",sa.String(160),nullable=False),
        sa.Column("category",sa.String(50),nullable=False),
        sa.Column("serial_reference",sa.String(120),nullable=True),
        sa.Column("status",sa.String(25),nullable=False),
        sa.Column("description",sa.String(1000),nullable=False),
        sa.Column("next_service_on",sa.Date(),nullable=True),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("status IN ('IN_SERVICE','NEEDS_SERVICE','OUT_OF_SERVICE','RETIRED')",
                           name="ck_property_asset_status"),
        sa.UniqueConstraint("property_id","serial_reference",name="uq_asset_property_serial"))
    op.create_index("ix_property_assets_property","property_assets",["property_id"])
    op.create_index("ix_property_assets_room","property_assets",["room_id"])
    op.create_index("ix_property_assets_status_service","property_assets",["status","next_service_on"])

def downgrade():
    op.drop_index("ix_property_assets_status_service",table_name="property_assets")
    op.drop_index("ix_property_assets_room",table_name="property_assets")
    op.drop_index("ix_property_assets_property",table_name="property_assets")
    op.drop_table("property_assets")
