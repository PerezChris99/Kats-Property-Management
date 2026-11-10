"""Data-subject request triage with role-safe visibility and no destructive shortcuts."""
from datetime import datetime, timezone
from flask import Blueprint, abort, jsonify
from flask_jwt_extended import jwt_required
from .api import current_user, roles, data, required_string, serialize, fail, audit, list_page
from .extensions import db
from .models import Tenant, Lease, Invoice
from .privacy_models import PrivacyRequest
from sqlalchemy import func

privacy_api = Blueprint("privacy_requests",__name__)
KINDS = {"ACCESS","RECTIFY","ERASURE","RESTRICT","OBJECT"}

@privacy_api.get("/privacy/my-data")
@jwt_required()
def personal_snapshot():
    user=current_user()
    profile={"full_name":user.full_name,"email":user.email,"role":user.role}
    linked=db.session.query(Tenant).filter_by(user_id=user.id).first()
    if not linked:
        return jsonify(account=profile,tenant=None,
                       notice="This is only a basic account summary. Request a complete export using the privacy request process.")
    outstanding=db.session.query(func.coalesce(func.sum(
        Invoice.total_ugx - Invoice.credit_ugx - Invoice.paid_ugx),0)).filter(
        Invoice.tenant_id==linked.id,Invoice.status!="VOID").scalar()
    active=db.session.query(Lease).filter_by(tenant_id=linked.id,status="ACTIVE").all()
    return jsonify(account=profile,
        tenant=serialize(linked,"id","full_name","phone","email"),
        active_leases=[serialize(x,"id","room_id","start_date","end_date","status") for x in active],
        outstanding_ugx=int(outstanding),
        notice="This is a summary only. Submit an access request for the full personal-data record.")

@privacy_api.post("/privacy/requests")
@jwt_required()
def submit_privacy_request():
    user=current_user()
    obj=data()
    kind=required_string(obj,"kind",25).upper()
    if kind not in KINDS:return fail("Unknown data protection request")
    details=required_string(obj,"details",2000)
    tenant_id=db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
    record=PrivacyRequest(requester_user_id=user.id,tenant_id=tenant_id,
                          kind=kind,details=details)
    db.session.add(record);db.session.flush()
    audit(user,"privacy.request_created","privacy_request",record.id,kind=kind)
    db.session.commit()
    return jsonify(request=serialize(record,"id","kind","status","created_at"),
                   notice="Request submitted for manual privacy review; no financial records were deleted"),201

@privacy_api.get("/privacy/requests")
@jwt_required()
def list_privacy_requests():
    user=current_user()
    query=db.session.query(PrivacyRequest)
    if user.role not in ("OWNER","SUPER_ADMIN"):
        query=query.filter_by(requester_user_id=user.id)
    results=list_page(PrivacyRequest,query.order_by(PrivacyRequest.created_at.desc()))
    # Ordinary users only see their own cases; privileged reviewers may triage.
    fields=("id","kind","details","status","decision_notes","created_at","reviewed_at")
    return jsonify(items=[dict(**serialize(x,*fields),
        **({"requester_user_id":x.requester_user_id} if user.role in ("OWNER","SUPER_ADMIN") else {}))
        for x in results.items],total=results.total)

@privacy_api.post("/privacy/requests/<request_id>/review")
@roles("OWNER","SUPER_ADMIN")
def review_privacy_request(user,request_id):
    obj=data()
    status=required_string(obj,"status",25).upper()
    if status not in ("IN_REVIEW","COMPLETED","DECLINED"):
        return fail("Invalid request review state")
    notes=required_string(obj,"decision_notes",2000)
    record=db.session.query(PrivacyRequest).filter_by(id=request_id).with_for_update().first()
    if not record:abort(404)
    if record.status in ("COMPLETED","DECLINED"):
        return fail("Closed privacy requests cannot be silently rewritten",409)
    if status=="COMPLETED" and record.kind=="ERASURE" and not obj.get("retention_exceptions_reviewed"):
        return fail("Erasure completion requires documented retention and statutory exceptions review",409)
    record.status=status
    record.decision_notes=notes
    record.reviewed_by=user.id
    record.reviewed_at=datetime.now(timezone.utc)
    audit(user,"privacy.request_reviewed","privacy_request",record.id,
          outcome=status,kind=record.kind)
    db.session.commit()
    return jsonify(request=serialize(record,"id","kind","status","reviewed_at"),
                   notice="Review status updated; fulfillment remains an operator responsibility.")
