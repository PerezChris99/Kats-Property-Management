"""Auditable water/electricity meters, readings and one-time approved billing.

Readings use integer thousandths of the unit (kWh or m3) to avoid float
rounding; each charge is snapshotted. A reading never credits a paid invoice
or silently sends money through a provider.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from .api import current_user, roles, data, ugx, required_string, parse_date, fail, serialize, audit, list_page
from .extensions import db
from .models import Room, Lease, Invoice, InvoiceLine, LedgerEntry, Tenant, CaretakerAssignment
from .utility_models import UtilityMeter, UtilityReading

utility_api = Blueprint("utilities", __name__)
STAFF = {"OWNER", "MANAGER", "ACCOUNTANT", "SUPER_ADMIN"}
READERS = {"OWNER", "MANAGER", "SUPER_ADMIN", "CARETAKER"}

def scope_query(user, query):
    if user.role == "TENANT":
        linked = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if not linked:
            return query.filter(False)
        assigned = db.session.query(Lease.room_id).filter_by(tenant_id=linked, status="ACTIVE")
        return query.filter(UtilityMeter.room_id.in_(assigned))
    if user.role == "CARETAKER":
        assigned = db.session.query(CaretakerAssignment.room_id).filter_by(caretaker_user_id=user.id)
        return query.filter(UtilityMeter.room_id.in_(assigned))
    if user.role not in STAFF:
        abort(403)
    return query

def visible_meter(user, meter_id):
    return scope_query(user, db.session.query(UtilityMeter).filter_by(id=meter_id)).first()

@utility_api.get("/utilities/meters")
@jwt_required()
def list_meters():
    user=current_user()
    query=scope_query(user,db.session.query(UtilityMeter))
    if request.args.get("room_id"):
        query=query.filter(UtilityMeter.room_id==request.args["room_id"])
    rows=list_page(UtilityMeter,query.order_by(UtilityMeter.created_at.desc()))
    return jsonify(items=[serialize(m,"id","room_id","kind","tariff_ugx_per_unit",
        "baseline_milli_units","created_at") for m in rows.items],total=rows.total)

@utility_api.post("/utilities/meters")
@roles("OWNER","MANAGER","SUPER_ADMIN")
def register_meter(user):
    obj=data()
    room=db.session.get(Room,required_string(obj,"room_id"))
    if not room: abort(404)
    kind=required_string(obj,"kind",20).upper()
    if kind not in ("WATER","ELECTRICITY"): return fail("Unsupported utility meter kind")
    tariff=ugx(obj.get("tariff_ugx_per_unit"),positive=True)
    baseline=ugx(obj.get("baseline_milli_units",0))
    meter=UtilityMeter(room_id=room.id,kind=kind,tariff_ugx_per_unit=tariff,
                       baseline_milli_units=baseline,created_by=user.id)
    db.session.add(meter)
    try:
        db.session.flush()
        audit(user,"utility.meter_created","utility_meter",meter.id,kind=kind,room_id=room.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Meter already registered for this room and utility",409)
    return jsonify(meter=serialize(meter,"id","room_id","kind","tariff_ugx_per_unit",
        "baseline_milli_units")),201

@utility_api.get("/utilities/meters/<meter_id>/readings")
@jwt_required()
def list_readings(meter_id):
    user=current_user()
    meter=visible_meter(user,meter_id)
    if not meter:abort(404)
    results=list_page(UtilityReading,db.session.query(UtilityReading)
        .filter_by(meter_id=meter_id).order_by(UtilityReading.observed_on.desc(),UtilityReading.created_at.desc()))
    return jsonify(items=[serialize(row,"id","previous_milli_units","current_milli_units",
        "used_milli_units","tariff_ugx_per_unit","charge_ugx","observed_on",
        "invoice_line_id","created_at") for row in results.items],total=results.total)

@utility_api.post("/utilities/meters/<meter_id>/readings")
@jwt_required()
def record_reading(meter_id):
    user=current_user()
    if user.role not in READERS:abort(403)
    obj=data()
    # The meter lock serializes two simultaneous readings from the same device.
    meter=db.session.query(UtilityMeter).filter_by(id=meter_id).with_for_update().first()
    if not meter or not visible_meter(user,meter_id):abort(404)
    key=required_string(obj,"idempotency_key",128)
    current=ugx(obj.get("current_milli_units"))
    observed=parse_date(obj.get("observed_on"))
    if observed>datetime.now(ZoneInfo("Africa/Kampala")).date():
        return fail("A meter reading cannot be dated in the future",409)
    replay=db.session.query(UtilityReading).filter_by(idempotency_key=key).first()
    if replay:
        if replay.meter_id!=meter.id or replay.current_milli_units!=current or replay.observed_on!=observed:
            return fail("Idempotency key reused for different readings",409)
        return jsonify(reading=serialize(replay,"id","charge_ugx","invoice_line_id"),reused=True)
    previous_record=db.session.query(UtilityReading).filter_by(meter_id=meter.id).order_by(
        UtilityReading.observed_on.desc(),UtilityReading.created_at.desc()).first()
    previous=previous_record.current_milli_units if previous_record else meter.baseline_milli_units
    if (current<previous or (previous_record and observed<previous_record.observed_on)):
        return fail("Meter reading must be monotonic in usage and date",409)
    used=current-previous
    charge=(used*meter.tariff_ugx_per_unit+500)//1000
    if charge>10**15:return fail("Computed charge exceeds safe bounds",409)
    row=UtilityReading(meter_id=meter.id,previous_milli_units=previous,
        current_milli_units=current,used_milli_units=used,
        tariff_ugx_per_unit=meter.tariff_ugx_per_unit,
        charge_ugx=charge,observed_on=observed,
        idempotency_key=key,recorded_by=user.id)
    db.session.add(row)
    try:
        db.session.flush()
        audit(user,"utility.reading_recorded","utility_reading",row.id,
              meter_id=meter.id,used_milli_units=used,charge_ugx=charge)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Duplicate utility reading command",409)
    return jsonify(reading=serialize(row,"id","meter_id","charge_ugx",
        "used_milli_units","observed_on"),notice="Reading is not billed until separately approved"),201

@utility_api.post("/utilities/readings/<reading_id>/apply")
@roles("OWNER","ACCOUNTANT","SUPER_ADMIN")
def bill_reading(user,reading_id):
    obj=data()
    reading=db.session.query(UtilityReading).filter_by(id=reading_id).with_for_update().first()
    if not reading:abort(404)
    if reading.invoice_line_id:
        return fail("Reading is already billed; never bill the same usage twice",409)
    if reading.recorded_by == user.id:
        return fail("Utility billing requires an independent approver",403)
    meter=db.session.get(UtilityMeter,reading.meter_id)
    invoice=db.session.query(Invoice).filter_by(id=required_string(obj,"invoice_id")).with_for_update().first()
    if not invoice:abort(404)
    lease=db.session.get(Lease,invoice.lease_id)
    if (not lease or lease.room_id!=meter.room_id or invoice.status!="ISSUED"
            or invoice.paid_ugx or invoice.credit_ugx
            or not invoice.period_start<=reading.observed_on<=invoice.period_end):
        return fail("Utility reading requires a matching, unmodified, unpaid invoice for its period",409)
    if reading.charge_ugx==0:
        return fail("Zero-consumption readings cannot generate a bill",409)
    line=InvoiceLine(invoice_id=invoice.id,charge_type=meter.kind,
        description=f"{meter.kind.title()} meter {reading.previous_milli_units/1000:g} to {reading.current_milli_units/1000:g} units",
        quantity=1,unit_price_ugx=reading.charge_ugx,amount_ugx=reading.charge_ugx)
    db.session.add(line)
    db.session.flush()
    reading.invoice_line_id=line.id
    invoice.total_ugx+=reading.charge_ugx
    db.session.add(LedgerEntry(invoice_id=invoice.id,event="INVOICE_UTILITY_ADDED",
                               amount_ugx=reading.charge_ugx))
    audit(user,"utility.reading_billed","utility_reading",reading.id,
          invoice_id=invoice.id,amount_ugx=reading.charge_ugx)
    db.session.commit()
    return jsonify(reading_id=reading.id,invoice_id=invoice.id,
                   added_ugx=reading.charge_ugx,invoice_total_ugx=invoice.total_ugx)
