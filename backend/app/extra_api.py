"""Authenticated operational routes with safe third-party boundaries."""
from datetime import datetime, timezone
import os
import uuid
from flask import Blueprint, abort, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from .extensions import db, limiter
from .api import current_user, roles, data, required_string, ugx, serialize, audit, list_page, fail
from .models import User, Room, Lease, Tenant, Invoice, MaintenanceRequest, CaretakerAssignment
from .extra_models import Notification, WorkOrder, Document, FiscalSubmission, LegalPage, SystemSetting, ContactRequest

extra_api = Blueprint("extra_api", __name__)
LEGAL_SLUGS = {"privacy", "terms", "cookies", "refund", "data-protection", "acceptable-use", "disclaimer", "accessibility"}
DOCUMENT_TYPES = {"LEASE", "ID", "RECEIPT", "INSPECTION", "PAYMENT_PROOF", "ROOM_PHOTO"}
MIME = {"application/pdf", "image/jpeg", "image/png", "image/webp"}

def assigned_to(caretaker, room_id):
    return bool(db.session.query(CaretakerAssignment.id).filter_by(
        caretaker_user_id=caretaker.id, room_id=room_id
    ).first())

@extra_api.get("/public/legal/<slug>")
def published_legal(slug):
    if slug not in LEGAL_SLUGS:
        abort(404)
    page = db.session.query(LegalPage).filter_by(slug=slug, published=True).order_by(
        LegalPage.version.desc()).first()
    if not page:
        return fail("Legal page is not published", 404)
    return jsonify(page=serialize(page, "slug", "version", "title", "content", "created_at"))

@extra_api.get("/admin/legal-pages")
@roles("OWNER", "SUPER_ADMIN")
def list_legal(user):
    rows = db.session.query(LegalPage).order_by(LegalPage.slug, LegalPage.version.desc()).limit(200).all()
    return jsonify(items=[serialize(p, "id", "slug", "version", "title", "published", "created_at") for p in rows])

@extra_api.post("/admin/legal-pages")
@roles("OWNER", "SUPER_ADMIN")
def legal_version(user):
    obj = data()
    slug = required_string(obj, "slug", 60)
    if slug not in LEGAL_SLUGS:
        return fail("Unsupported legal page type")
    content = required_string(obj, "content", 100000)
    title = required_string(obj, "title", 200)
    # New content is a draft; publication is a separate explicit action.
    latest = db.session.query(func.max(LegalPage.version)).filter_by(slug=slug).scalar() or 0
    page = LegalPage(slug=slug, version=latest+1, title=title, content=content,
                     published=False, created_by=user.id)
    db.session.add(page)
    try:
        db.session.flush()
        audit(user, "legal.create_version", "legal_page", page.id, slug=slug, version=page.version)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Conflicting legal page version; retry", 409)
    return jsonify(page=serialize(page, "id", "slug", "version", "published")), 201

@extra_api.post("/admin/legal-pages/<page_id>/publish")
@roles("OWNER", "SUPER_ADMIN")
def publish_legal(user, page_id):
    page = db.session.get(LegalPage, page_id)
    if not page:
        abort(404)
    if not page.published:
        page.published = True
        audit(user, "legal.publish", "legal_page", page.id, slug=page.slug, version=page.version)
        db.session.commit()
    return jsonify(page=serialize(page, "id", "slug", "version", "published"))

@extra_api.get("/notifications")
@jwt_required()
def user_notifications():
    user = current_user()
    results = list_page(Notification, db.session.query(Notification).filter_by(user_id=user.id).order_by(
        Notification.created_at.desc()))
    return jsonify(items=[serialize(n, "id", "kind", "title", "body", "channel", "status", "read_at",
                                    "created_at") for n in results.items], total=results.total,
                   next_cursor=getattr(results, "next_cursor", None))

@extra_api.post("/notifications/<notification_id>/read")
@jwt_required()
def mark_read(notification_id):
    user = current_user()
    notification = db.session.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
    if not notification:
        abort(404)
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.session.commit()
    return jsonify(notification=serialize(notification, "id", "read_at"))

@extra_api.get("/maintenance/<request_id>/work-orders")
@jwt_required()
def work_orders(request_id):
    user = current_user()
    job = db.session.get(MaintenanceRequest, request_id)
    if not job:
        abort(404)
    if user.role == "TENANT":
        linked = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if linked is None or job.tenant_id != linked:
            abort(404)
    elif user.role == "CARETAKER":
        if not assigned_to(user, job.room_id):
            abort(404)
    elif user.role not in {"OWNER", "MANAGER", "ACCOUNTANT", "SUPER_ADMIN"}:
        abort(403)
    rows = db.session.query(WorkOrder).filter_by(request_id=job.id).order_by(WorkOrder.assigned_at.desc()).limit(100).all()
    return jsonify(items=[serialize(w, "id", "request_id", "scope", "status", "estimated_cost_ugx",
                                    "actual_cost_ugx", "assigned_at", "completed_at") for w in rows])

@extra_api.post("/maintenance/<request_id>/work-orders")
@roles("OWNER", "MANAGER", "SUPER_ADMIN")
def create_work_order(user, request_id):
    job = db.session.get(MaintenanceRequest, request_id)
    if not job:
        abort(404)
    if job.status in ("REJECTED", "CANCELLED", "COMPLETED"):
        return fail("Maintenance request is closed", 409)
    obj = data()
    assigned = obj.get("assigned_user_id")
    if assigned:
        worker = db.session.get(User, assigned)
        if not worker or worker.role not in ("CARETAKER", "MANAGER") or not worker.is_active:
            return fail("Invalid technician/employee")
        if worker.role == "CARETAKER" and not assigned_to(worker, job.room_id):
            return fail("Caretaker must be assigned to this room")
    work = WorkOrder(request_id=job.id, assigned_user_id=assigned,
                     contractor_name=obj.get("contractor_name"),
                     scope=required_string(obj, "scope", 3000),
                     estimated_cost_ugx=ugx(obj.get("estimated_cost_ugx", 0)))
    job.status = "ASSIGNED"
    db.session.add(work)
    db.session.flush()
    audit(user, "maintenance.work_order", "work_order", work.id, request_id=request_id)
    db.session.commit()
    return jsonify(work_order=serialize(work, "id", "status", "request_id")), 201

@extra_api.post("/work-orders/<work_id>/status")
@roles("OWNER", "MANAGER", "SUPER_ADMIN")
def complete_work_order(user, work_id):
    work = db.session.query(WorkOrder).filter_by(id=work_id).with_for_update().first()
    if not work:
        abort(404)
    obj = data()
    state = required_string(obj, "status").upper()
    if state not in ("IN_PROGRESS", "ON_HOLD", "COMPLETED", "CANCELLED"):
        return fail("Invalid work order state")
    if work.status in ("CANCELLED", "COMPLETED") and state != work.status:
        return fail("Finalized work orders require a separate correction", 409)
    cost = ugx(obj.get("actual_cost_ugx", work.actual_cost_ugx))
    work.status = state
    work.actual_cost_ugx = cost
    if state == "COMPLETED":
        work.completed_at = datetime.now(timezone.utc)
    audit(user, "maintenance.work_order_status", "work_order", work.id, state=state, actual_cost_ugx=cost)
    db.session.commit()
    return jsonify(work_order=serialize(work, "id", "status", "actual_cost_ugx"))

@extra_api.post("/efris/queue")
@roles("OWNER", "ACCOUNTANT", "SUPER_ADMIN")
def queue_efris(user):
    obj = data()
    invoice_id = required_string(obj, "invoice_id")
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice or invoice.status == "VOID":
        return fail("A valid invoice is required")
    key = "efris-invoice-" + invoice.id
    existing = db.session.query(FiscalSubmission).filter_by(idempotency_key=key).first()
    if existing:
        return jsonify(submission=serialize(existing, "id", "invoice_id", "state")), 200
    item = FiscalSubmission(invoice_id=invoice.id, document_type="INVOICE", idempotency_key=key,
                            state="PENDING_FISCALIZATION",
                            payload={"invoice_number":invoice.invoice_number, "net_amount_ugx":
                                     invoice.total_ugx-invoice.credit_ugx, "paid_ugx":invoice.paid_ugx})
    db.session.add(item)
    try:
        db.session.flush()
        audit(user, "efris.queue", "efris_submission", item.id, invoice_id=invoice.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Fiscal submission already queued", 409)
    return jsonify(submission=serialize(item, "id", "invoice_id", "state"),
                   notice="Queued only. No URA fiscal document was issued."), 202

@extra_api.get("/efris")
@roles("OWNER", "ACCOUNTANT", "SUPER_ADMIN")
def efris_queue(user):
    results = list_page(FiscalSubmission, db.session.query(FiscalSubmission).order_by(
        FiscalSubmission.created_at.desc()))
    return jsonify(items=[serialize(f, "id", "invoice_id", "document_type", "state",
                                    "fiscal_document_number", "attempt_count", "created_at")
                          for f in results.items], total=results.total)

@extra_api.get("/admin/system-settings")
@roles("OWNER", "SUPER_ADMIN")
def settings_list(user):
    rows = db.session.query(SystemSetting).order_by(SystemSetting.key).limit(200).all()
    return jsonify(items=[serialize(x, "key", "value", "updated_at") for x in rows])

@extra_api.put("/admin/system-settings/<key>")
@roles("OWNER", "SUPER_ADMIN")
def setting_update(user, key):
    if key not in ("rent_reminder_days", "business_display_name", "support_email", "default_late_fee_days"):
        return fail("Setting cannot be modified from public API", 403)
    obj = data()
    val = obj.get("value")
    if key in ("rent_reminder_days", "default_late_fee_days"):
        if type(val) is not int or not 0 <= val <= 60:
            return fail("Setting must be integer from 0 to 60")
    elif not isinstance(val, str) or len(val) > 200:
        return fail("Setting must be text no longer than 200 characters")
    item = db.session.get(SystemSetting, key)
    if item is None:
        item = SystemSetting(key=key, value=val, updated_by=user.id)
        db.session.add(item)
    else:
        item.value = val
        item.updated_by = user.id
        item.updated_at = datetime.now(timezone.utc)
    audit(user, "system.setting", "setting", user.id, key=key)
    db.session.commit()
    return jsonify(setting=serialize(item, "key", "value"))


@extra_api.post("/public/access-requests")
@extra_api.post("/public/contact-requests")  # Existing clients; do not break the API.
@limiter.limit("3 per hour")
def public_contact():
    obj=data()
    # Honeypot blocks trivial scripted spam without collecting more personal data.
    if obj.get("website"):
        return jsonify(message="Request accepted"),202
    full_name=required_string(obj,"full_name",160)
    email=required_string(obj,"email",254).lower()
    import re
    if not re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",email):
        return fail("Enter a valid email address")
    message=required_string(obj,"message",3000)
    if len(message)<20:
        return fail("Please include at least 20 characters describing your request")
    subject=required_string(obj,"subject",120)
    if subject not in ("ACCESS","DEMO","PRICING","SUPPORT","OTHER"):
        return fail("Invalid request subject")
    if obj.get("consent") is not True:
        return fail("Privacy consent is required")
    phone=obj.get("phone")
    if phone is not None and (not isinstance(phone,str) or len(phone)>30):
        return fail("Invalid optional phone")
    record=ContactRequest(full_name=full_name,email=email,phone=phone,subject=subject,
                          message=message,consent=True,status="NEW")
    db.session.add(record)
    db.session.commit()
    return jsonify(request_id=record.id,message=("Request submitted for administrator review. No account has been created." if subject == "ACCESS" else "Your request has been recorded.")),201

@extra_api.get("/admin/contact-requests")
@roles("OWNER","SUPER_ADMIN")
def contact_inbox(user):
    results=list_page(ContactRequest,db.session.query(ContactRequest).order_by(ContactRequest.created_at.desc()))
    return jsonify(items=[serialize(r,"id","full_name","email","phone","subject",
                                    "message","status","created_at") for r in results.items],
                   total=results.total)

@extra_api.post("/admin/contact-requests/<request_id>/resolve")
@roles("OWNER","SUPER_ADMIN")
def contact_review(user,request_id):
    req=db.session.get(ContactRequest,request_id)
    if not req:
        abort(404)
    status=required_string(data(),"status",20).upper()
    if status not in ("NEW","IN_PROGRESS","RESOLVED","SPAM"):
        return fail("Invalid inquiry status")
    req.status=status
    req.reviewed_by=user.id
    req.reviewed_at=datetime.now(timezone.utc)
    audit(user,"contact.review","contact_request",req.id,status=status)
    db.session.commit()
    return jsonify(inquiry=serialize(req,"id","status"))
