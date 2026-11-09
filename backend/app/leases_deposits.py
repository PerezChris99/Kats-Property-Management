"""Lease amendments and accounting-only deposit movement approvals."""
from datetime import timedelta, datetime, timezone
from flask import Blueprint, abort, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from .extensions import db
from .api import roles, current_user, data, parse_date, ugx, required_string, serialize, fail, audit, list_page
from .models import Lease, LeaseAmendment, DepositMovement, Tenant, Inspection

lifecycle_api = Blueprint("lease_lifecycle", __name__)
FINANCE = {"OWNER", "MANAGER", "ACCOUNTANT", "SUPER_ADMIN"}

def rent_at(lease, target):
    latest = db.session.query(LeaseAmendment).filter(
        LeaseAmendment.lease_id == lease.id, LeaseAmendment.effective_date <= target
    ).order_by(LeaseAmendment.effective_date.desc()).first()
    return latest.new_rent_ugx if latest else lease.rent_ugx

def balance(lease_id):
    events = db.session.query(DepositMovement.kind, func.coalesce(func.sum(DepositMovement.amount_ugx),0)).filter(
        DepositMovement.lease_id == lease_id,DepositMovement.status == "APPROVED"
    ).group_by(DepositMovement.kind).all()
    amounts = {kind:int(amount) for kind,amount in events}
    held=amounts.get("HOLD",0)
    returned=amounts.get("REFUND",0)
    withheld=amounts.get("WITHHOLD",0)
    return {"held_ugx":held,"refunded_ugx":returned,"withheld_ugx":withheld,
            "available_ugx":held-returned-withheld}

def visible_lease(user, lease_id):
    lease=db.session.get(Lease,lease_id)
    if not lease:
        abort(404)
    if user.role=="TENANT":
        tenant_id=db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if tenant_id is None or lease.tenant_id != tenant_id:
            abort(404)
    elif user.role not in FINANCE:
        abort(403)
    return lease

@lifecycle_api.get("/leases/<lease_id>/amendments")
@jwt_required()
def amendments(lease_id):
    user=current_user()
    lease=visible_lease(user,lease_id)
    rows=db.session.query(LeaseAmendment).filter_by(lease_id=lease.id).order_by(
        LeaseAmendment.effective_date.desc()).all()
    return jsonify(items=[serialize(x,"id","previous_end_date","new_end_date","effective_date",
                                    "previous_rent_ugx","new_rent_ugx","reason","created_at") for x in rows])

@lifecycle_api.post("/leases/<lease_id>/renew")
@roles("OWNER", "MANAGER", "SUPER_ADMIN")
def renew_lease(user,lease_id):
    obj=data()
    reason=required_string(obj,"reason",500)
    new_end=parse_date(obj.get("new_end_date"))
    lease=db.session.query(Lease).filter_by(id=lease_id).with_for_update().first()
    if not lease:
        abort(404)
    if lease.status!="ACTIVE" or new_end<=lease.end_date:
        return fail("Renewal requires an active lease and a later end date",409)
    current_rent=rent_at(lease,lease.end_date)
    new_rent=ugx(obj.get("new_rent_ugx",current_rent),positive=True)
    change=LeaseAmendment(
        lease_id=lease.id,previous_end_date=lease.end_date,new_end_date=new_end,
        effective_date=lease.end_date+timedelta(days=1),
        previous_rent_ugx=current_rent,new_rent_ugx=new_rent,
        reason=reason,created_by=user.id)
    lease.end_date=new_end
    db.session.add(change)
    db.session.flush()
    audit(user,"lease.renew","lease",lease.id,amendment_id=change.id,
          previous_rent_ugx=current_rent,new_rent_ugx=new_rent,
          effective_date=change.effective_date.isoformat())
    db.session.commit()
    return jsonify(lease=serialize(lease,"id","end_date","status"),
                   amendment=serialize(change,"id","effective_date","new_rent_ugx")),201

@lifecycle_api.get("/deposits/leases/<lease_id>")
@jwt_required()
def deposit_summary(lease_id):
    user=current_user()
    lease=visible_lease(user,lease_id)
    entries=db.session.query(DepositMovement).filter_by(lease_id=lease.id).order_by(
        DepositMovement.created_at.desc()).limit(200).all()
    return jsonify(balance=balance(lease.id),items=[serialize(m,"id","kind","amount_ugx",
                               "status","reason","created_at") for m in entries])

@lifecycle_api.get("/deposits")
@roles("OWNER","MANAGER","ACCOUNTANT","SUPER_ADMIN")
def list_deposits(user):
    results=list_page(DepositMovement,db.session.query(DepositMovement).order_by(
        DepositMovement.created_at.desc()))
    return jsonify(items=[serialize(m,"id","lease_id","kind","amount_ugx","status",
                                   "created_at") for m in results.items],total=results.total)

@lifecycle_api.post("/deposits/movements")
@roles("OWNER","MANAGER","ACCOUNTANT","SUPER_ADMIN")
def record_deposit(user):
    obj=data()
    lease=db.session.get(Lease,required_string(obj,"lease_id"))
    if not lease:
        abort(404)
    kind=required_string(obj,"kind",20).upper()
    if kind not in ("HOLD","REFUND","WITHHOLD"):
        return fail("Unknown deposit movement type")
    reason=required_string(obj,"reason",500)
    key=required_string(obj,"idempotency_key",128)
    amount=ugx(obj.get("amount_ugx"),positive=True)
    existing=db.session.query(DepositMovement).filter_by(idempotency_key=key).first()
    if existing:
        if existing.lease_id!=lease.id or existing.kind!=kind or existing.amount_ugx!=amount or existing.created_by!=user.id:
            return fail("Duplicate idempotency key for different deposit data",409)
        return jsonify(movement=serialize(existing,"id","kind","status")),200
    reference=obj.get("external_reference")
    if kind in ("HOLD","REFUND"):
        if not isinstance(reference,str) or not 3<=len(reference.strip())<=160:
            return fail("Verified bank/cash reference is required for money movement")
    if kind in ("REFUND","WITHHOLD"):
        if lease.status!="TERMINATED":
            return fail("Move-out settlement requires terminated lease",409)
        if not db.session.query(Inspection.id).filter_by(lease_id=lease.id,kind="MOVE_OUT").first():
            return fail("Move-out inspection is required",409)
    item=DepositMovement(lease_id=lease.id,kind=kind,amount_ugx=amount,reason=reason,
                         idempotency_key=key,external_reference=reference,created_by=user.id,
                         status="PENDING_REVIEW")
    db.session.add(item)
    try:
        db.session.flush()
        audit(user,"deposit.pending","deposit_movement",item.id,kind=kind)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Duplicate deposit command",409)
    return jsonify(movement=serialize(item,"id","lease_id","amount_ugx","kind","status"),
                   notice="Awaiting verification by another authorized staff member."),201

@lifecycle_api.post("/deposits/movements/<movement_id>/review")
@roles("OWNER","ACCOUNTANT","SUPER_ADMIN")
def review_deposit(user,movement_id):
    obj=data()
    decision=required_string(obj,"decision",20).upper()
    if decision not in ("APPROVE","REJECT"):
        return fail("Decision must be APPROVE or REJECT")
    reason=required_string(obj,"reason",500)
    pending=db.session.get(DepositMovement,movement_id)
    if not pending:
        abort(404)
    # Single lease lock serializes multiple approvals to prevent overspending deposit.
    lease=db.session.query(Lease).filter_by(id=pending.lease_id).with_for_update().first()
    movement=db.session.query(DepositMovement).filter_by(id=movement_id).with_for_update().first()
    if movement.status!="PENDING_REVIEW":
        return fail("Deposit movement already reviewed",409)
    if movement.created_by==user.id:
        return fail("Deposit movement requires a separate reviewer",403)
    if decision=="APPROVE":
        current=balance(lease.id)
        if movement.kind=="HOLD":
            if current["held_ugx"]+movement.amount_ugx>lease.deposit_ugx:
                return fail("Deposit held would exceed lease security deposit",409)
        elif movement.amount_ugx>current["available_ugx"]:
            return fail("Deposit movement exceeds verified held funds",409)
        if movement.kind=="WITHHOLD":
            inspected=db.session.query(Inspection).filter_by(
                lease_id=lease.id,kind="MOVE_OUT").order_by(Inspection.created_at.desc()).first()
            if not inspected or current["withheld_ugx"] + movement.amount_ugx > inspected.damage_estimate_ugx:
                return fail("Cumulative withholding exceeds recorded move-out damage estimate",409)
    movement.status="APPROVED" if decision=="APPROVE" else "REJECTED"
    movement.reviewed_by=user.id
    movement.reviewed_at=datetime.now(timezone.utc)
    audit(user,"deposit.review","deposit_movement",movement.id,decision=decision,reason=reason)
    db.session.commit()
    return jsonify(movement=serialize(movement,"id","kind","amount_ugx","status"),
                   balance=balance(lease.id),
                   warning="Accounting approval records verified evidence but does not transfer funds.")
