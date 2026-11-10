"""Tenant-visible disputes with documented status events and owner-only resolution.

Records are not court decisions. They preserve the written complaint,
acknowledgements, responses and internal staff decisions without claiming a
legal notice has been delivered or a refund paid.
"""
from datetime import datetime,timezone
from flask import Blueprint, abort, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from .extensions import db
from .api import current_user, roles, required_string, data, fail, serialize, audit, list_page
from .models import Lease,Tenant
from .dispute_models import TenancyDispute,DisputeEvent

dispute_api=Blueprint("tenant_disputes",__name__)
STAFF={"OWNER","MANAGER","SUPER_ADMIN","ACCOUNTANT"}
REVIEWERS={"OWNER","MANAGER","SUPER_ADMIN"}
KINDS={"RENT","DEPOSIT","REPAIR","SERVICE","NOTICE","OTHER"}

def scoped_cases(user):
    query=db.session.query(TenancyDispute)
    if user.role=="TENANT":
        tenant_id=db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        return query.filter(TenancyDispute.tenant_id==tenant_id) if tenant_id else query.filter(False)
    if user.role not in STAFF:abort(403)
    return query

def visible(user,dispute_id,lock=False):
    query=scoped_cases(user).filter(TenancyDispute.id==dispute_id)
    if lock:query=query.with_for_update()
    record=query.first()
    if record is None:abort(404)
    return record

@dispute_api.get("/disputes")
@jwt_required()
def list_disputes():
    user=current_user()
    results=list_page(TenancyDispute,scoped_cases(user).order_by(TenancyDispute.created_at.desc()))
    return jsonify(items=[serialize(x,"id","lease_id","tenant_id","kind",
        "title","description","status","created_at","updated_at","closed_at")
        for x in results.items],total=results.total)

@dispute_api.post("/disputes")
@jwt_required()
def open_dispute():
    user=current_user()
    if user.role not in STAFF|{"TENANT"}:abort(403)
    obj=data()
    lease=db.session.get(Lease,required_string(obj,"lease_id"))
    if not lease:abort(404)
    if user.role=="TENANT":
        tenant_id=db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if tenant_id!=lease.tenant_id:abort(404)
    kind=required_string(obj,"kind",24).upper()
    if kind not in KINDS:return fail("Invalid dispute type")
    title=required_string(obj,"title",160)
    details=required_string(obj,"description",3000)
    record=TenancyDispute(lease_id=lease.id,tenant_id=lease.tenant_id,
        kind=kind,title=title,description=details,opened_by=user.id)
    db.session.add(record);db.session.flush()
    db.session.add(DisputeEvent(dispute_id=record.id,actor_id=user.id,
        event="OPENED",comment=details,new_status="OPEN"))
    audit(user,"dispute.opened","tenancy_dispute",record.id,lease_id=lease.id,kind=kind)
    db.session.commit()
    return jsonify(dispute=serialize(record,"id","lease_id","kind","title","status","created_at"),
        notice="An internal dispute record is not a court filing or official notice."),201

@dispute_api.get("/disputes/<dispute_id>/events")
@jwt_required()
def dispute_events(dispute_id):
    user=current_user()
    visible(user,dispute_id)
    results=list_page(DisputeEvent,db.session.query(DisputeEvent)
        .filter_by(dispute_id=dispute_id).order_by(DisputeEvent.created_at.asc()))
    return jsonify(items=[serialize(e,"id","actor_id","event","comment",
        "previous_status","new_status","created_at") for e in results.items],total=results.total)

@dispute_api.post("/disputes/<dispute_id>/comments")
@jwt_required()
def comment_on_dispute(dispute_id):
    user=current_user()
    record=visible(user,dispute_id,lock=True)
    if record.status in ("RESOLVED","DECLINED"):
        return fail("Resolved disputes require a new dispute or formal reopening",409)
    comment=required_string(data(),"comment",3000)
    item=DisputeEvent(dispute_id=record.id,actor_id=user.id,event="COMMENTED",comment=comment)
    db.session.add(item)
    record.updated_at=datetime.now(timezone.utc)
    audit(user,"dispute.comment","tenancy_dispute",record.id)
    db.session.commit()
    return jsonify(event=serialize(item,"id","event","created_at")),201

@dispute_api.post("/disputes/<dispute_id>/decision")
@roles("OWNER","MANAGER","SUPER_ADMIN")
def decide_dispute(user,dispute_id):
    record=visible(user,dispute_id,lock=True)
    obj=data()
    state=required_string(obj,"status",24).upper()
    if state not in ("OPEN","IN_REVIEW","RESOLVED","DECLINED"):
        return fail("Unsupported dispute status")
    if state==record.status:return fail("Dispute already in requested state",409)
    if record.status in ("RESOLVED","DECLINED") and state!="OPEN":
        return fail("Closed disputes may only be formally reopened",409)
    comment=required_string(obj,"reason",3000)
    previous=record.status
    record.status=state
    record.updated_at=datetime.now(timezone.utc)
    record.reviewed_by=user.id
    record.closed_at=record.updated_at if state in ("RESOLVED","DECLINED") else None
    event=DisputeEvent(dispute_id=record.id,actor_id=user.id,
        event=("REOPENED" if previous in ("RESOLVED","DECLINED") else "STATUS_CHANGED"),
        comment=comment,previous_status=previous,new_status=state)
    db.session.add(event)
    audit(user,"dispute.status","tenancy_dispute",record.id,previous=previous,new=state)
    db.session.commit()
    return jsonify(dispute=serialize(record,"id","status","closed_at"),
        notice="Internal disposition only; no cash transfer or legal eviction is executed")
