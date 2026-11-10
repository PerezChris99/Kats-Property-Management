"""Utility meters/readings are separate from invoiced revenue until approved."""
from .extensions import db
from .models import new_id, utcnow, CheckConstraint

class UtilityMeter(db.Model):
    __tablename__ = "utility_meters"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    room_id = db.Column(db.String(36), db.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    kind = db.Column(db.String(20), nullable=False)
    tariff_ugx_per_unit = db.Column(db.BigInteger, nullable=False)
    baseline_milli_units = db.Column(db.BigInteger, nullable=False, default=0)
    created_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        db.UniqueConstraint("room_id", "kind", name="uq_meter_room_kind"),
        CheckConstraint("tariff_ugx_per_unit > 0 AND baseline_milli_units >= 0", name="ck_meter_tariff"),
        CheckConstraint("kind IN ('WATER','ELECTRICITY')", name="ck_meter_kind"),
    )

class UtilityReading(db.Model):
    __tablename__ = "utility_readings"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    meter_id = db.Column(db.String(36), db.ForeignKey("utility_meters.id", ondelete="RESTRICT"), nullable=False, index=True)
    previous_milli_units = db.Column(db.BigInteger, nullable=False)
    current_milli_units = db.Column(db.BigInteger, nullable=False)
    used_milli_units = db.Column(db.BigInteger, nullable=False)
    tariff_ugx_per_unit = db.Column(db.BigInteger, nullable=False)
    charge_ugx = db.Column(db.BigInteger, nullable=False)
    observed_on = db.Column(db.Date, nullable=False)
    idempotency_key = db.Column(db.String(128), nullable=False, unique=True)
    invoice_line_id = db.Column(db.String(36), db.ForeignKey("invoice_lines.id", ondelete="RESTRICT"), unique=True)
    recorded_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        CheckConstraint("current_milli_units >= previous_milli_units AND previous_milli_units >= 0", name="ck_utility_reading_monotonic"),
        CheckConstraint("used_milli_units = current_milli_units - previous_milli_units", name="ck_utility_consumption"),
        CheckConstraint("charge_ugx >= 0 AND tariff_ugx_per_unit > 0", name="ck_utility_charge"),
        db.Index("ix_utility_readings_meter_date", "meter_id", "observed_on"),
    )
