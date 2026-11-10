"""Role-scoped preventive-maintenance schedules.

A schedule generates a normal maintenance request for staff follow-up;
no contractor is authorized, no money is disbursed, and mandatory safety
inspections remain a separate legal/compliance requirement.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint,abort,jsonify
from flask_jwt_extended import jwt_required
from .extensions import db
from .api import roles,current_user,data,required_string,parse_date,fail,serialize,list_page,audit
from .models import Room,CaretakerAssignment
from .maintenance_plan_models import MaintenancePlan,MaintenanceOccurrence

maintenance_plan_api=Blueprint("maintenance_plans",__name__)

def scoped(user):
    query=db.session.query(MaintenancePlan)
    if user.role=="CARETAKER":
        assigned=db.session.query(CaretakerAssignment.room_id).filter_by(caretaker_user_id=user.id)
        return query.filter(MaintenancePlan.room_id.in_(assigned))
    if user.role not in ("OWNER","MANAGER","ACCOUNTANT","SUPER_ADMIN"):
        abort(403)
    return query

@maintenance_plan_api.get("/maintenance/plans")
@jwt_required()
def list_plans():
    user=current_user()
    results=list_page(MaintenancePlan,scoped(user).order_by(MaintenancePlan.next_due_on.asc()))
    return jsonify(items=[serialize(x,"id","room_id","title","instructions",
        "priority","cadence_days","next_due_on","status","created_at")
        for x in results.items],total=results.total)

@maintenance_plan_api.post("/maintenance/plans")
@roles("OWNER","MANAGER","SUPER_ADMIN")
def create_plan(user):
    obj=data()
    room=db.session.get(Room,required_string(obj,"room_id"))
    if room is None or room.status=="ARCHIVED":
        return fail("Active, non-archived room required",404)
    title=required_string(obj,"title",120)
    instructions=required_string(obj,"instructions",2500)
    priority=required_string(obj,"priority",20).upper()
    if priority not in ("LOW","MEDIUM","HIGH","URGENT"):
        return fail("Invalid maintenance priority")
    cadence=obj.get("cadence_days")
    if type(cadence) is not int or not 1<=cadence<=366:
        return fail("Cadence must be 1–366 days")
    due=parse_date(obj.get("next_due_on"))
    if due<datetime.now(ZoneInfo("Africa/Kampala")).date():
        return fail("Initial planned inspection cannot be in the past",409)
    plan=MaintenancePlan(room_id=room.id,title=title,instructions=instructions,
        priority=priority,cadence_days=cadence,next_due_on=due,created_by=user.id)
    db.session.add(plan);db.session.flush()
    audit(user,"maintenance.plan_created","maintenance_plan",plan.id,room_id=room.id)
    db.session.commit()
    return jsonify(plan=serialize(plan,"id","room_id","title","cadence_days","next_due_on","status")),201

@maintenance_plan_api.post("/maintenance/plans/<plan_id>/status")
@roles("OWNER","MANAGER","SUPER_ADMIN")
def set_plan_status(user,plan_id):
    obj=data()
    status=required_string(obj,"status",20).upper()
    if status not in ("ACTIVE","PAUSED","RETIRED"):
        return fail("Unsupported maintenance plan state")
    plan=db.session.query(MaintenancePlan).filter_by(id=plan_id).with_for_update().first()
    if not plan:abort(404)
    if plan.status=="RETIRED" and status!="RETIRED":
        return fail("Retired maintenance plans cannot be silently reactivated",409)
    reason=required_string(obj,"reason",500)
    old=plan.status
    if old==status:return fail("Plan is already in that state",409)
    plan.status=status
    plan.updated_at=datetime.now(ZoneInfo("Africa/Kampala"))
    audit(user,"maintenance.plan_state","maintenance_plan",plan.id,
          old_status=old,new_status=status,reason=reason)
    db.session.commit()
    return jsonify(plan=serialize(plan,"id","status","next_due_on"))

@maintenance_plan_api.get("/maintenance/plans/<plan_id>/occurrences")
@jwt_required()
def list_occurrences(plan_id):
    user=current_user()
    plan=scoped(user).filter_by(id=plan_id).first()
    if not plan:abort(404)
    results=list_page(MaintenanceOccurrence,db.session.query(MaintenanceOccurrence)
        .filter_by(plan_id=plan.id).order_by(MaintenanceOccurrence.scheduled_for.desc()))
    return jsonify(items=[serialize(x,"id","scheduled_for","maintenance_request_id",
        "created_at") for x in results.items],total=results.total)
