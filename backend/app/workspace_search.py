"""Global workspace search with per-role result scoping and hard row limits."""
from flask import Blueprint, jsonify, request, abort
from sqlalchemy import or_
from .api import roles
from .extensions import db
from .models import Property, Tenant, Invoice, MaintenanceRequest, Room, CaretakerAssignment

workspace_search_api = Blueprint("workspace_search", __name__)
STAFF = ("OWNER","MANAGER","ACCOUNTANT","SUPER_ADMIN")


def _literal(term):
    return "%" + term.replace("\\","\\\\").replace("%","\\%").replace("_","\\_") + "%"


@workspace_search_api.get("/workspace/search")
@roles(*STAFF, "TENANT", "CARETAKER")
def global_search(user):
    term = request.args.get("q","").strip()
    if not 2 <= len(term) <= 80:
        abort(400,description="Search requires 2–80 characters")
    pattern = _literal(term)
    hits = []

    def add(kind, label, value, path, detail=""):
        hits.append({"kind":kind,"label":label,"value":str(value),
                     "path":path,"detail":detail})

    if user.role in STAFF:
        for property_record in (db.session.query(Property).filter(or_(
                Property.name.ilike(pattern,escape="\\"),
                Property.district.ilike(pattern,escape="\\")
            )).order_by(Property.name,Property.id).limit(8).all()):
            add("property",property_record.name,property_record.id,"/properties",property_record.district)
        for tenant in (db.session.query(Tenant).filter(or_(
                Tenant.full_name.ilike(pattern,escape="\\"),
                Tenant.phone.ilike(pattern,escape="\\"),
                Tenant.email.ilike(pattern,escape="\\")
            )).order_by(Tenant.full_name,Tenant.id).limit(8).all()):
            add("tenant",tenant.full_name,tenant.id,"/tenants","Tenant profile")

    if user.role in STAFF or user.role=="TENANT":
        invoices = db.session.query(Invoice)
        repairs = db.session.query(MaintenanceRequest)
        if user.role == "TENANT":
            tenant_id = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
            if not tenant_id:
                return jsonify(items=[],total_returned=0,limited=True)
            invoices = invoices.filter(Invoice.tenant_id == tenant_id)
            repairs = repairs.filter(MaintenanceRequest.tenant_id == tenant_id)
        for invoice in (invoices.filter(Invoice.invoice_number.ilike(
                pattern,escape="\\")).order_by(Invoice.invoice_number,Invoice.id).limit(8).all()):
            add("invoice",invoice.invoice_number,invoice.id,"/invoices",invoice.status)
        for ticket in (repairs.filter(MaintenanceRequest.title.ilike(
                pattern,escape="\\")).order_by(MaintenanceRequest.created_at.desc(),
                MaintenanceRequest.id.desc()).limit(8).all()):
            add("maintenance",ticket.title,ticket.id,"/maintenance",ticket.status)

    if user.role == "CARETAKER":
        for room in (db.session.query(Room).join(
                CaretakerAssignment, CaretakerAssignment.room_id==Room.id
            ).filter(CaretakerAssignment.caretaker_user_id == user.id,
                Room.number.ilike(pattern,escape="\\")
            ).order_by(Room.number,Room.id).limit(8).all()):
            add("room",room.number,room.id,"/rooms",room.status)

    return jsonify(items=hits,total_returned=len(hits),limited=True,
                   notice="Results are restricted to your account permissions and limited per record category.")
