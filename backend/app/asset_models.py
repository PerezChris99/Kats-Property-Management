"""Private asset inventory for one property business.

Assets are operational records, not a subscription/catalog offering.
"""
from .extensions import db
from .models import new_id, utcnow

class PropertyAsset(db.Model):
    __tablename__ = "property_assets"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    property_id = db.Column(db.String(36), db.ForeignKey("properties.id", ondelete="RESTRICT"),
                            nullable=False, index=True)
    room_id = db.Column(db.String(36), db.ForeignKey("rooms.id", ondelete="RESTRICT"),
                        nullable=True, index=True)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="OTHER")
    serial_reference = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(25), nullable=False, default="IN_SERVICE")
    description = db.Column(db.String(1000), nullable=False, default="")
    next_service_on = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        db.CheckConstraint("status IN ('IN_SERVICE','NEEDS_SERVICE','OUT_OF_SERVICE','RETIRED')",
                           name="ck_property_asset_status"),
        db.UniqueConstraint("property_id", "serial_reference", name="uq_asset_property_serial"),
    )
