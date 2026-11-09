from datetime import date, datetime, timezone
from functools import wraps
import os
from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token, get_jwt_identity, get_jwt, decode_token,
    jwt_required, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
)
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from .extensions import db, limiter
from .models import (
    User, RefreshSession, Property, Room, RoomStateHistory, Tenant, Lease,
    Invoice, Payment, LedgerEntry, MaintenanceRequest, Expense, AuditLog, CaretakerAssignment, Inspection
)

api = Blueprint("api", __name__)
hasher = PasswordHasher()
STAFF = {"SUPER_ADMIN", "OWNER", "MANAGER", "ACCOUNTANT"}
OPERATIONS = {"SUPER_ADMIN", "OWNER", "MANAGER"}
ROOM_STATES = {"VACANT", "OCCUPIED", "RESERVED", "NOTICE_GIVEN", "CLEANING", "MAINTENANCE", "UNAVAILABLE", "DISPUTE", "ARCHIVED"}

def fail(message, status=400):
    return jsonify(error={"code": "REQUEST_REJECTED", "message": message}), status

def data():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        abort(400, description="JSON object required")
    return value

def required_string(obj, key, max_length=250):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        abort(400, description=key + " is required and must be text")
    return value.strip()

def ugx(value, positive=False):
    if type(value) is not int or value < (1 if positive else 0) or value > 10**15:
        abort(400, description="Amount must be a non-negative integer UGX value")
    return value

def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        abort(400, description="Invalid date; expected YYYY-MM-DD")

def serialize(obj, *names):
    result = {}
    for name in names:
        value = getattr(obj, name)
        result[name] = value.isoformat() if isinstance(value, date) else value
    return result

def audit(actor, action, target, target_id, **details):
    db.session.add(AuditLog(actor_id=actor.id, action=action, target_type=target, target_id=target_id, details=details))

def current_user():
    user = db.session.get(User, get_jwt_identity())
    if not user or not user.is_active:
        abort(403)
    if get_jwt().get("sv") != user.session_version:
        abort(401, description="Session expired; sign in again")
    return user

def roles(*allowed):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args, **kwargs):
            user = current_user()
            if user.role not in allowed:
                abort(403)
            return fn(user, *args, **kwargs)
        return wrapped
    return decorator

def list_page(model, query):
    try:
        page = min(max(int(request.args.get("page", 1)), 1), 100000)
        size = min(max(int(request.args.get("page_size", 25)), 1), 100)
    except ValueError:
        abort(400)
    return query.paginate(page=page, per_page=size, error_out=False)

@api.post("/auth/register")
@limiter.limit("5 per hour")
def register():
    if os.getenv("PUBLIC_REGISTRATION_ENABLED", "false").lower() != "true":
        return fail("Registration is invitation-only", 403)
    obj = data()
    email = required_string(obj, "email").lower()
    name = required_string(obj, "full_name", 160)
    password = required_string(obj, "password", 256)
    if len(password) < 12 or "@" not in email:
        return fail("Valid email and password of at least 12 characters required")
    if db.session.query(User.id).filter_by(email=email).first():
        return fail("Account already exists", 409)
    user = User(email=email, full_name=name, password_hash=hasher.hash(password), role="TENANT")
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Account already exists", 409)
    return jsonify(user=serialize(user, "id", "full_name", "role")), 201

@api.post("/auth/login")
@limiter.limit("10 per minute")
def login():
    obj = data()
    email = required_string(obj, "email").lower()
    password = required_string(obj, "password", 256)
    user = db.session.query(User).filter_by(email=email).first()
    try:
        valid = bool(user and user.is_active and hasher.verify(user.password_hash, password))
    except (VerifyMismatchError, VerificationError):
        valid = False
    if not valid:
        return fail("Invalid email or password", 401)
    response = jsonify(user=serialize(user, "id", "full_name", "role"))
    claims = {"sv": user.session_version}
    refresh_token = create_refresh_token(identity=user.id, additional_claims=claims)
    from datetime import datetime, timezone
    expiry = datetime.fromtimestamp(decode_token(refresh_token)["exp"], tz=timezone.utc)
    db.session.add(RefreshSession(user_id=user.id, token_jti=decode_token(refresh_token)["jti"], expires_at=expiry))
    audit(user, "auth.login", "user", user.id)
    db.session.commit()
    set_access_cookies(response, create_access_token(identity=user.id, additional_claims=claims))
    set_refresh_cookies(response, refresh_token)
    return response

@api.post("/auth/refresh")
@jwt_required(refresh=True)
def refresh():
    from .models import utcnow
    token = get_jwt()
    user = current_user()
    session = db.session.query(RefreshSession).filter_by(
        token_jti=token["jti"], user_id=user.id, revoked_at=None
    ).with_for_update().first()
    if session is None or session.expires_at.replace(tzinfo=timezone.utc) <= utcnow():
        return fail("Refresh session expired or already used", 401)
    claims = {"sv": user.session_version}
    new_refresh = create_refresh_token(identity=user.id, additional_claims=claims)
    expiry = datetime.fromtimestamp(decode_token(new_refresh)["exp"], tz=timezone.utc)
    session.revoked_at = utcnow()
    db.session.add(RefreshSession(user_id=user.id, token_jti=decode_token(new_refresh)["jti"], expires_at=expiry))
    db.session.commit()
    response = jsonify(user=serialize(user, "id", "full_name", "role"))
    set_access_cookies(response, create_access_token(identity=user.id, additional_claims=claims))
    set_refresh_cookies(response, new_refresh)
    return response

@api.post("/auth/logout")
@jwt_required()
def logout():
    user = current_user()
    user.session_version += 1
    db.session.query(RefreshSession).filter_by(user_id=user.id, revoked_at=None).update(
        {RefreshSession.revoked_at: datetime.now(timezone.utc)}, synchronize_session=False
    )
    audit(user, "auth.logout", "user", user.id)
    db.session.commit()
    response = jsonify(message="Signed out from all devices")
    unset_jwt_cookies(response)
    return response

@api.post("/auth/change-password")
@jwt_required()
@limiter.limit("5 per hour")
def change_password():
    user = current_user()
    obj = data()
    current = required_string(obj, "current_password", 256)
    updated = required_string(obj, "new_password", 256)
    if len(updated) < 12 or updated == current:
        return fail("A different password of at least 12 characters is required")
    try:
        valid = hasher.verify(user.password_hash, current)
    except (VerifyMismatchError, VerificationError):
        valid = False
    if not valid:
        return fail("Incorrect current password", 403)
    user.password_hash = hasher.hash(updated)
    user.session_version += 1
    db.session.query(RefreshSession).filter_by(user_id=user.id, revoked_at=None).update(
        {RefreshSession.revoked_at: datetime.now(timezone.utc)}, synchronize_session=False
    )
    audit(user, "auth.change_password", "user", user.id)
    db.session.commit()
    response = jsonify(message="Password changed; please sign in again")
    unset_jwt_cookies(response)
    return response

@api.get("/auth/me")
@jwt_required()
def me():
    user = current_user()
    return jsonify(user=serialize(user, "id", "full_name", "role"))

@api.get("/public/landing-content")
def landing_content():
    return jsonify(title="Manage your rentals, collect rent, and stay compliant.",
                   currency="UGX", provider_status="not configured")

@api.get("/properties")
@roles(*STAFF)
def properties(user):
    results = list_page(Property, db.session.query(Property).order_by(Property.name))
    return jsonify(items=[serialize(p, "id", "name", "address", "district") for p in results.items], total=results.total, page=results.page)

@api.post("/properties")
@roles(*OPERATIONS)
def add_property(user):
    obj = data()
    p = Property(name=required_string(obj, "name", 200), address=required_string(obj, "address", 400), district=required_string(obj, "district", 120))
    db.session.add(p)
    db.session.flush()
    audit(user, "property.create", "property", p.id)
    db.session.commit()
    return jsonify(property=serialize(p, "id", "name", "address", "district")), 201

@api.get("/rooms")
@roles(*STAFF)
def rooms(user):
    query = db.session.query(Room)
    if request.args.get("property_id"):
        query = query.filter_by(property_id=request.args["property_id"])
    results = list_page(Room, query.order_by(Room.number))
    return jsonify(items=[serialize(r, "id", "property_id", "number", "status", "rent_ugx", "deposit_ugx") for r in results.items], total=results.total)

@api.post("/rooms")
@roles(*OPERATIONS)
def add_room(user):
    obj = data()
    property_id = required_string(obj, "property_id")
    if not db.session.get(Property, property_id):
        abort(404)
    room = Room(property_id=property_id, number=required_string(obj, "number", 60), rent_ugx=ugx(obj.get("rent_ugx")), deposit_ugx=ugx(obj.get("deposit_ugx", 0)))
    db.session.add(room)
    try:
        db.session.flush()
        audit(user, "room.create", "room", room.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Room number already exists for the property", 409)
    return jsonify(room=serialize(room, "id", "number", "status", "rent_ugx", "property_id")), 201

@api.post("/rooms/<room_id>/status")
@roles(*OPERATIONS)
def change_room_status(user, room_id):
    obj = data()
    room = db.session.get(Room, room_id)
    if not room:
        abort(404)
    new_status = required_string(obj, "status")
    reason = required_string(obj, "reason", 500)
    if new_status not in ROOM_STATES:
        return fail("Unknown room state")
    if db.session.query(Lease.id).filter_by(room_id=room_id, status="ACTIVE").first() and new_status == "VACANT":
        return fail("Cannot mark a leased room vacant", 409)
    old = room.status
    room.status = new_status
    db.session.add(RoomStateHistory(room_id=room.id, old_status=old, new_status=new_status, reason=reason, actor_id=user.id))
    audit(user, "room.status", "room", room.id, previous=old, new=new_status)
    db.session.commit()
    return jsonify(room=serialize(room, "id", "status"))

@api.get("/tenants")
@roles(*STAFF)
def tenants(user):
    results = list_page(Tenant, db.session.query(Tenant).order_by(Tenant.full_name))
    return jsonify(items=[serialize(t, "id", "full_name", "phone", "email") for t in results.items], total=results.total)

@api.post("/tenants")
@roles(*OPERATIONS)
def add_tenant(user):
    obj = data()
    tenant = Tenant(full_name=required_string(obj, "full_name", 160), phone=required_string(obj, "phone", 30), email=obj.get("email"))
    if obj.get("user_id"):
        account = db.session.get(User, obj["user_id"])
        if not account or account.role != "TENANT":
            return fail("Linked user must have tenant role")
        tenant.user_id = account.id
    db.session.add(tenant)
    try:
        db.session.flush()
        audit(user, "tenant.create", "tenant", tenant.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Account already linked to a tenant", 409)
    return jsonify(tenant=serialize(tenant, "id", "full_name", "phone")), 201

@api.get("/leases")
@roles(*STAFF)
def leases(user):
    results = list_page(Lease, db.session.query(Lease).order_by(Lease.start_date.desc()))
    return jsonify(items=[serialize(lease, "id", "room_id", "tenant_id", "start_date", "end_date", "status", "rent_ugx") for lease in results.items], total=results.total)

@api.post("/leases")
@roles(*OPERATIONS)
def add_lease(user):
    obj = data()
    room = db.session.get(Room, required_string(obj, "room_id"))
    tenant = db.session.get(Tenant, required_string(obj, "tenant_id"))
    if not room or not tenant:
        abort(404)
    if room.status != "VACANT":
        return fail("Room must be vacant", 409)
    start, end = parse_date(obj.get("start_date")), parse_date(obj.get("end_date"))
    if end <= start:
        return fail("Lease end must follow start")
    lease = Lease(room_id=room.id, tenant_id=tenant.id, start_date=start, end_date=end,
                  rent_ugx=ugx(obj.get("rent_ugx"), positive=True), deposit_ugx=ugx(obj.get("deposit_ugx", 0)),
                  due_day=obj.get("due_day", 1))
    if type(lease.due_day) is not int or not 1 <= lease.due_day <= 28:
        return fail("Due day must be an integer between 1 and 28")
    db.session.add(lease)
    room.status = "OCCUPIED"
    try:
        db.session.flush()
        db.session.add(RoomStateHistory(room_id=room.id, old_status="VACANT", new_status="OCCUPIED",
                                        reason="Lease started", actor_id=user.id))
        audit(user, "lease.create", "lease", lease.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Conflicting active lease", 409)
    return jsonify(lease=serialize(lease, "id", "room_id", "tenant_id", "status")), 201

@api.get("/invoices")
@jwt_required()
def invoices():
    user = current_user()
    query = db.session.query(Invoice)
    if user.role == "TENANT":
        linked = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if linked is None:
            return jsonify(items=[], total=0)
        query = query.filter_by(tenant_id=linked)
    elif user.role not in STAFF:
        abort(403)
    results = list_page(Invoice, query.order_by(Invoice.created_at.desc()))
    fields = ("id", "invoice_number", "lease_id", "tenant_id", "period_start", "period_end", "due_date", "total_ugx", "paid_ugx", "status")
    return jsonify(items=[serialize(inv, *fields) for inv in results.items], total=results.total)

@api.post("/invoices")
@roles(*STAFF)
def add_invoice(user):
    obj = data()
    lease = db.session.get(Lease, required_string(obj, "lease_id"))
    if not lease or lease.status != "ACTIVE":
        return fail("Active lease required")
    start, end, due = [parse_date(obj.get(key)) for key in ("period_start", "period_end", "due_date")]
    if end < start or start < lease.start_date or end > lease.end_date:
        return fail("Billing period outside lease bounds")
    total = ugx(obj.get("total_ugx"), positive=True)
    from .models import new_id
    invoice = Invoice(lease_id=lease.id, tenant_id=lease.tenant_id, period_start=start, period_end=end,
                      due_date=due, total_ugx=total, invoice_number="KATS-" + new_id()[:12].upper())
    db.session.add(invoice)
    try:
        db.session.flush()
        db.session.add(LedgerEntry(invoice_id=invoice.id, event="INVOICE_ISSUED", amount_ugx=total))
        audit(user, "invoice.issue", "invoice", invoice.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Invoice already exists for billing period", 409)
    return jsonify(invoice=serialize(invoice, "id", "invoice_number", "total_ugx", "status")), 201

@api.get("/payments")
@jwt_required()
def payments():
    user = current_user()
    query = db.session.query(Payment).join(Invoice, Invoice.id == Payment.invoice_id)
    if user.role == "TENANT":
        linked = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if linked is None:
            return jsonify(items=[], total=0)
        query = query.filter(Invoice.tenant_id == linked)
    elif user.role not in STAFF:
        abort(403)
    results = list_page(Payment, query.order_by(Payment.created_at.desc()))
    return jsonify(items=[serialize(p, "id", "invoice_id", "amount_ugx", "method", "status", "created_at") for p in results.items], total=results.total)

@api.post("/payments/manual")
@roles(*STAFF)
def record_manual_payment(user):
    obj = data()
    method = required_string(obj, "method").upper()
    if method not in ("CASH", "BANK_TRANSFER"):
        return fail("Only cash and bank proof are accepted here")
    invoice = db.session.get(Invoice, required_string(obj, "invoice_id"))
    if not invoice or invoice.status in ("VOID", "PAID"):
        return fail("Open invoice required")
    key = required_string(obj, "idempotency_key", 128)
    existing = db.session.query(Payment).filter_by(idempotency_key=key).first()
    if existing:
        intended_amount = ugx(obj.get("amount_ugx"), positive=True)
        if (existing.invoice_id != invoice.id or existing.amount_ugx != intended_amount
                or existing.method != method):
            return fail("Idempotency key already used for a different payment", 409)
        return jsonify(payment=serialize(existing, "id", "status", "amount_ugx")), 200
    amount = ugx(obj.get("amount_ugx"), positive=True)
    if amount > invoice.total_ugx - invoice.paid_ugx:
        return fail("Payment is greater than outstanding invoice balance")
    reference = obj.get("reference")
    if method == "BANK_TRANSFER":
        if not isinstance(reference, str) or not reference.strip():
            return fail("Bank transfer requires a reference")
    payment = Payment(invoice_id=invoice.id, amount_ugx=amount, method=method,
                      reference=reference, idempotency_key=key, created_by=user.id,
                      status="PENDING_REVIEW")
    db.session.add(payment)
    try:
        db.session.flush()
        audit(user, "payment.record_unverified", "payment", payment.id, method=method)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Duplicate reference or idempotency key", 409)
    return jsonify(payment=serialize(payment, "id", "status", "amount_ugx")), 201

@api.post("/payments/<payment_id>/approve")
@roles(*STAFF)
def approve_payment(user, payment_id):
    if user.role == "TENANT":
        abort(403)
    payment = db.session.query(Payment).filter_by(id=payment_id).with_for_update().first()
    if not payment:
        abort(404)
    if payment.status == "RECONCILED":
        return jsonify(payment=serialize(payment, "id", "status")), 200
    if payment.status != "PENDING_REVIEW":
        return fail("Payment is not awaiting review", 409)
    if payment.created_by == user.id:
        return fail("Payment must be approved by a different staff member", 403)
    invoice = db.session.query(Invoice).filter_by(id=payment.invoice_id).with_for_update().first()
    if invoice.status == "VOID" or payment.amount_ugx > invoice.total_ugx - invoice.paid_ugx:
        return fail("Payment conflicts with current invoice balance", 409)
    invoice.paid_ugx += payment.amount_ugx
    invoice.status = "PAID" if invoice.paid_ugx == invoice.total_ugx else "PARTIALLY_PAID"
    payment.status = "RECONCILED"
    payment.reviewed_by = user.id
    db.session.add(LedgerEntry(invoice_id=invoice.id, payment_id=payment.id,
                               event="PAYMENT_RECEIVED", amount_ugx=payment.amount_ugx))
    audit(user, "payment.approve", "payment", payment.id)
    db.session.commit()
    return jsonify(payment=serialize(payment, "id", "status"), invoice=serialize(invoice, "id", "status", "paid_ugx"))

@api.get("/maintenance")
@jwt_required()
def maintenance_list():
    user = current_user()
    query = db.session.query(MaintenanceRequest)
    if user.role == "TENANT":
        tenant_id = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if not tenant_id:
            return jsonify(items=[], total=0)
        query = query.filter_by(tenant_id=tenant_id)
    elif user.role not in STAFF:
        abort(403)
    results = list_page(MaintenanceRequest, query.order_by(MaintenanceRequest.created_at.desc()))
    return jsonify(items=[serialize(m, "id", "room_id", "title", "priority", "status") for m in results.items], total=results.total)

@api.post("/maintenance")
@jwt_required()
def maintenance_create():
    user = current_user()
    obj = data()
    room = db.session.get(Room, required_string(obj, "room_id"))
    if not room:
        abort(404)
    tenant_id = None
    if user.role == "TENANT":
        tenant_id = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if not tenant_id or not db.session.query(Lease.id).filter_by(tenant_id=tenant_id, room_id=room.id, status="ACTIVE").first():
            abort(403)
    elif user.role not in STAFF:
        abort(403)
    priority = str(obj.get("priority", "MEDIUM")).upper()
    if priority not in ("LOW", "MEDIUM", "HIGH", "URGENT"):
        return fail("Invalid priority")
    req = MaintenanceRequest(room_id=room.id, tenant_id=tenant_id, title=required_string(obj, "title", 160),
                             description=required_string(obj, "description", 3000), priority=priority)
    db.session.add(req)
    db.session.flush()
    audit(user, "maintenance.create", "maintenance", req.id)
    db.session.commit()
    return jsonify(request=serialize(req, "id", "status", "title")), 201

@api.get("/expenses")
@roles(*STAFF)
def expenses(user):
    results = list_page(Expense, db.session.query(Expense).order_by(Expense.incurred_on.desc()))
    return jsonify(items=[serialize(e, "id", "property_id", "category", "amount_ugx", "incurred_on") for e in results.items], total=results.total)

@api.post("/expenses")
@roles(*STAFF)
def add_expense(user):
    obj = data()
    prop = db.session.get(Property, required_string(obj, "property_id"))
    if not prop:
        abort(404)
    expense = Expense(property_id=prop.id, category=required_string(obj, "category", 80),
                      description=required_string(obj, "description", 500),
                      amount_ugx=ugx(obj.get("amount_ugx")),
                      incurred_on=parse_date(obj.get("incurred_on")), created_by=user.id)
    db.session.add(expense)
    db.session.flush()
    audit(user, "expense.record", "expense", expense.id)
    db.session.commit()
    return jsonify(expense=serialize(expense, "id", "amount_ugx")), 201

@api.get("/dashboard")
@roles(*STAFF)
def dashboard(user):
    rooms_count = db.session.query(func.count(Room.id)).scalar() or 0
    occupied = db.session.query(func.count(Room.id)).filter(Room.status == "OCCUPIED").scalar() or 0
    expected = db.session.query(func.coalesce(func.sum(Invoice.total_ugx), 0)).scalar() or 0
    paid = db.session.query(func.coalesce(func.sum(Invoice.paid_ugx), 0)).scalar() or 0
    open_maintenance = db.session.query(func.count(MaintenanceRequest.id)).filter(MaintenanceRequest.status.in_(["OPEN","ASSIGNED","IN_PROGRESS","ON_HOLD"])).scalar() or 0
    return jsonify(rooms=rooms_count, occupied_rooms=occupied, vacant_rooms=max(0, rooms_count - occupied),
                   expected_ugx=int(expected), collected_ugx=int(paid), outstanding_ugx=int(expected - paid),
                   open_maintenance=open_maintenance)

@api.get("/integrations")
@roles(*STAFF)
def integrations(user):
    # Intentionally never claim connected based on mere presence of a flag.
    return jsonify(mtn_momo="NOT_VERIFIED", airtel_money="NOT_VERIFIED", efris="NOT_VERIFIED")

@api.get("/audit")
@roles("OWNER", "SUPER_ADMIN")
def audit_entries(user):
    results = list_page(AuditLog, db.session.query(AuditLog).order_by(AuditLog.created_at.desc()))
    return jsonify(items=[serialize(a, "id", "actor_id", "action", "target_type", "target_id", "created_at") for a in results.items], total=results.total)


@api.get("/tenant/lease")
@roles("TENANT")
def tenant_lease(user):
    tenant_id = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
    if not tenant_id:
        return jsonify(lease=None)
    lease = db.session.query(Lease).filter_by(tenant_id=tenant_id, status="ACTIVE").first()
    if not lease:
        return jsonify(lease=None)
    return jsonify(lease=serialize(lease, "id", "tenant_id", "room_id", "start_date", "end_date",
                                 "rent_ugx", "deposit_ugx", "due_day", "status"))

@api.get("/tenant/dashboard")
@roles("TENANT")
def tenant_dashboard(user):
    tenant_id = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
    if not tenant_id:
        return jsonify(total_ugx=0, paid_ugx=0, outstanding_ugx=0, invoices=0)
    total, paid, count = db.session.query(
        func.coalesce(func.sum(Invoice.total_ugx), 0),
        func.coalesce(func.sum(Invoice.paid_ugx), 0),
        func.count(Invoice.id)
    ).filter(Invoice.tenant_id == tenant_id).one()
    return jsonify(total_ugx=int(total), paid_ugx=int(paid),
                   outstanding_ugx=int(total - paid), invoices=int(count))


@api.post("/billing/generate-monthly")
@roles("OWNER", "MANAGER", "SUPER_ADMIN")
def generate_rent_for_month(user):
    from .billing import generate_monthly_rent
    month = parse_date(data().get("month"))
    return jsonify(result=generate_monthly_rent(month, actor=user))


def ensure_assigned(caretaker, room_id):
    assigned = db.session.query(CaretakerAssignment.id).filter_by(
        caretaker_user_id=caretaker.id, room_id=room_id
    ).first()
    if not assigned:
        abort(403)

@api.get("/caretaker/assignments")
@roles("OWNER", "MANAGER", "SUPER_ADMIN")
def caretaker_assignments(user):
    results = list_page(CaretakerAssignment, db.session.query(CaretakerAssignment).order_by(
        CaretakerAssignment.assigned_at.desc()
    ))
    return jsonify(items=[serialize(x, "id", "caretaker_user_id", "room_id", "assigned_at")
                          for x in results.items], total=results.total)

@api.post("/caretaker/assignments")
@roles("OWNER", "MANAGER", "SUPER_ADMIN")
def assign_caretaker(user):
    obj = data()
    caretaker = db.session.get(User, required_string(obj, "caretaker_user_id"))
    room = db.session.get(Room, required_string(obj, "room_id"))
    if not caretaker or caretaker.role != "CARETAKER" or not caretaker.is_active or not room:
        return fail("An active caretaker and an existing room are required")
    assignment = CaretakerAssignment(caretaker_user_id=caretaker.id, room_id=room.id)
    db.session.add(assignment)
    try:
        db.session.flush()
        audit(user, "caretaker.assign", "room", room.id, caretaker_id=caretaker.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Caretaker already assigned to this room", 409)
    return jsonify(assignment=serialize(assignment, "id", "caretaker_user_id", "room_id")), 201

@api.delete("/caretaker/assignments/<assignment_id>")
@roles("OWNER", "MANAGER", "SUPER_ADMIN")
def unassign_caretaker(user, assignment_id):
    assignment = db.session.get(CaretakerAssignment, assignment_id)
    if not assignment:
        abort(404)
    audit(user, "caretaker.unassign", "room", assignment.room_id,
          caretaker_id=assignment.caretaker_user_id)
    db.session.delete(assignment)
    db.session.commit()
    return jsonify(message="Assignment removed")

@api.get("/caretaker/dashboard")
@roles("CARETAKER")
def caretaker_dashboard(user):
    room_ids = db.session.query(CaretakerAssignment.room_id).filter_by(caretaker_user_id=user.id)
    assigned = db.session.query(func.count(Room.id)).filter(Room.id.in_(room_ids)).scalar() or 0
    open_requests = db.session.query(func.count(MaintenanceRequest.id)).filter(
        MaintenanceRequest.room_id.in_(room_ids),
        MaintenanceRequest.status.in_(["OPEN", "ASSIGNED", "IN_PROGRESS"])
    ).scalar() or 0
    pending_cash = db.session.query(func.count(Payment.id)).filter(
        Payment.created_by == user.id, Payment.status == "PENDING_REVIEW"
    ).scalar() or 0
    return jsonify(assigned_rooms=assigned, open_maintenance=open_requests,
                   pending_cash=pending_cash)

@api.get("/caretaker/rooms")
@roles("CARETAKER")
def caretaker_rooms(user):
    query = db.session.query(Room).join(
        CaretakerAssignment, CaretakerAssignment.room_id == Room.id
    ).filter(CaretakerAssignment.caretaker_user_id == user.id).order_by(Room.number)
    results = list_page(Room, query)
    return jsonify(items=[serialize(r, "id", "property_id", "number", "status")
                          for r in results.items], total=results.total)

@api.post("/caretaker/rooms/<room_id>/status")
@roles("CARETAKER")
def caretaker_room_status(user, room_id):
    ensure_assigned(user, room_id)
    obj = data()
    room = db.session.get(Room, room_id)
    if not room:
        abort(404)
    target = required_string(obj, "status").upper()
    if target not in {"CLEANING", "MAINTENANCE", "UNAVAILABLE", "NOTICE_GIVEN"}:
        return fail("Status requires manager approval")
    previous = room.status
    room.status = target
    db.session.add(RoomStateHistory(room_id=room.id, old_status=previous,
                                    new_status=target, reason=required_string(obj, "reason", 500),
                                    actor_id=user.id))
    audit(user, "caretaker.room_status", "room", room.id, previous=previous, new=target)
    db.session.commit()
    return jsonify(room=serialize(room, "id", "status"))

@api.get("/caretaker/maintenance")
@roles("CARETAKER")
def caretaker_maintenance(user):
    assigned_ids = db.session.query(CaretakerAssignment.room_id).filter_by(caretaker_user_id=user.id)
    query = db.session.query(MaintenanceRequest).filter(
        MaintenanceRequest.room_id.in_(assigned_ids)
    ).order_by(MaintenanceRequest.created_at.desc())
    results = list_page(MaintenanceRequest, query)
    return jsonify(items=[serialize(m, "id", "room_id", "title", "priority", "status")
                          for m in results.items], total=results.total)

@api.post("/caretaker/maintenance")
@roles("CARETAKER")
def caretaker_report_maintenance(user):
    obj = data()
    room_id = required_string(obj, "room_id")
    ensure_assigned(user, room_id)
    priority = str(obj.get("priority", "MEDIUM")).upper()
    if priority not in ("LOW", "MEDIUM", "HIGH", "URGENT"):
        return fail("Invalid priority")
    task = MaintenanceRequest(
        room_id=room_id, title=required_string(obj, "title", 160),
        description=required_string(obj, "description", 3000), priority=priority
    )
    db.session.add(task)
    db.session.flush()
    audit(user, "caretaker.maintenance", "maintenance", task.id)
    db.session.commit()
    return jsonify(request=serialize(task, "id", "title", "status")), 201

@api.get("/caretaker/payments")
@roles("CARETAKER")
def caretaker_payments(user):
    results = list_page(Payment, db.session.query(Payment).filter_by(
        created_by=user.id
    ).order_by(Payment.created_at.desc()))
    return jsonify(items=[serialize(p, "id", "invoice_id", "amount_ugx", "status", "method")
                          for p in results.items], total=results.total)

@api.post("/caretaker/payments")
@roles("CARETAKER")
def caretaker_record_cash(user):
    obj = data()
    invoice = db.session.get(Invoice, required_string(obj, "invoice_id"))
    if not invoice or invoice.status in ("PAID", "VOID"):
        return fail("Open invoice required")
    lease = db.session.get(Lease, invoice.lease_id)
    ensure_assigned(user, lease.room_id)
    amount = ugx(obj.get("amount_ugx"), positive=True)
    if amount > invoice.total_ugx - invoice.paid_ugx:
        return fail("Cash exceeds outstanding balance")
    key = required_string(obj, "idempotency_key", 128)
    existing = db.session.query(Payment).filter_by(idempotency_key=key).first()
    if existing:
        if (existing.invoice_id != invoice.id or existing.amount_ugx != amount
                or existing.method != "CASH"):
            return fail("Idempotency key already used for another payment", 409)
        return jsonify(payment=serialize(existing, "id", "status", "amount_ugx"))
    payment = Payment(invoice_id=invoice.id, amount_ugx=amount, method="CASH",
                      status="PENDING_REVIEW", idempotency_key=key, created_by=user.id)
    db.session.add(payment)
    try:
        db.session.flush()
        audit(user, "caretaker.cash_pending", "payment", payment.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Duplicate cash submission", 409)
    return jsonify(payment=serialize(payment, "id", "status", "amount_ugx")), 201


@api.get("/caretaker/invoices")
@roles("CARETAKER")
def caretaker_invoices(user):
    query = db.session.query(Invoice).join(Lease, Invoice.lease_id == Lease.id).join(
        CaretakerAssignment, CaretakerAssignment.room_id == Lease.room_id
    ).filter(CaretakerAssignment.caretaker_user_id == user.id).order_by(Invoice.created_at.desc())
    results = list_page(Invoice, query)
    return jsonify(items=[serialize(i, "id", "invoice_number", "total_ugx", "paid_ugx", "status", "due_date")
                          for i in results.items], total=results.total)

@api.get("/admin/users")
@roles("OWNER", "SUPER_ADMIN")
def admin_users(user):
    results = list_page(User, db.session.query(User).filter(
        User.role != "SERVICE").order_by(User.created_at.desc()))
    return jsonify(items=[serialize(account, "id", "full_name", "email", "role", "is_active")
                          for account in results.items], total=results.total)

@api.post("/admin/users")
@roles("OWNER", "SUPER_ADMIN")
def admin_create_user(user):
    obj = data()
    role = required_string(obj, "role").upper()
    if role not in ("MANAGER", "CARETAKER", "ACCOUNTANT", "TENANT"):
        return fail("This role cannot be created through the owner console", 403)
    email = required_string(obj, "email", 254).lower()
    name = required_string(obj, "full_name", 160)
    password = required_string(obj, "password", 256)
    if len(password) < 12 or "@" not in email:
        return fail("Provide a valid email and a 12+ character initial password")
    account = User(full_name=name, email=email, role=role,
                   password_hash=hasher.hash(password))
    db.session.add(account)
    try:
        db.session.flush()
        audit(user, "user.create", "user", account.id, role=role)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("This email already belongs to an account", 409)
    return jsonify(user=serialize(account, "id", "full_name", "email", "role")), 201

@api.post("/admin/users/<account_id>/status")
@roles("OWNER", "SUPER_ADMIN")
def admin_user_status(user, account_id):
    account = db.session.get(User, account_id)
    if not account or account.role == "SERVICE":
        abort(404)
    if account.id == user.id:
        return fail("You cannot deactivate your own session", 403)
    if account.role in ("SUPER_ADMIN", "OWNER") and user.role != "SUPER_ADMIN":
        abort(403)
    value = data().get("is_active")
    if type(value) is not bool:
        return fail("is_active must be a boolean")
    previous = account.is_active
    account.is_active = value
    if not value:
        account.session_version += 1
        db.session.query(RefreshSession).filter_by(user_id=account.id, revoked_at=None).update(
            {RefreshSession.revoked_at: datetime.now(timezone.utc)}, synchronize_session=False
        )
    audit(user, "user.status", "user", account.id, previous=previous, active=value)
    db.session.commit()
    return jsonify(user=serialize(account, "id", "full_name", "email", "role", "is_active"))


@api.post("/payments/<payment_id>/reverse")
@roles("OWNER", "ACCOUNTANT", "SUPER_ADMIN")
def reverse_payment(user, payment_id):
    """Accounting reversal only. This does not instruct a provider or bank to refund funds."""
    obj = data()
    reason = required_string(obj, "reason", 500)
    payment = db.session.query(Payment).filter_by(id=payment_id).with_for_update().first()
    if not payment:
        abort(404)
    if payment.status == "REVERSED":
        return jsonify(payment=serialize(payment, "id", "status")), 200
    if payment.status != "RECONCILED":
        return fail("Only reconciled payments can be reversed", 409)
    invoice = db.session.query(Invoice).filter_by(id=payment.invoice_id).with_for_update().first()
    if invoice.paid_ugx < payment.amount_ugx:
        return fail("Invoice balance and payment records are inconsistent", 409)
    invoice.paid_ugx -= payment.amount_ugx
    invoice.status = "ISSUED" if invoice.paid_ugx == 0 else "PARTIALLY_PAID"
    payment.status = "REVERSED"
    db.session.add(LedgerEntry(
        invoice_id=invoice.id, payment_id=payment.id,
        event="PAYMENT_REVERSED", amount_ugx=-payment.amount_ugx
    ))
    audit(user, "payment.reverse", "payment", payment.id,
          reason=reason, amount_ugx=payment.amount_ugx)
    db.session.commit()
    return jsonify(payment=serialize(payment, "id", "status"),
                   invoice=serialize(invoice, "id", "status", "paid_ugx"),
                   warning="Accounting adjustment recorded. No cash or provider refund executed.")

@api.post("/invoices/<invoice_id>/void")
@roles("OWNER", "ACCOUNTANT", "SUPER_ADMIN")
def void_invoice(user, invoice_id):
    reason = required_string(data(), "reason", 500)
    invoice = db.session.query(Invoice).filter_by(id=invoice_id).with_for_update().first()
    if not invoice:
        abort(404)
    if invoice.status == "VOID":
        return jsonify(invoice=serialize(invoice, "id", "status")), 200
    if invoice.paid_ugx != 0:
        return fail("Paid invoices require financial credit-note review", 409)
    if invoice.status not in ("ISSUED", "OVERDUE"):
        return fail("Cannot void this invoice state", 409)
    invoice.status = "VOID"
    db.session.add(LedgerEntry(
        invoice_id=invoice.id, event="INVOICE_VOIDED", amount_ugx=-invoice.total_ugx
    ))
    audit(user, "invoice.void", "invoice", invoice.id, reason=reason)
    db.session.commit()
    return jsonify(invoice=serialize(invoice, "id", "status"))


@api.get("/reports/summary")
@roles("OWNER", "MANAGER", "ACCOUNTANT", "SUPER_ADMIN")
def report_summary(user):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import calendar
    raw = request.args.get("month")
    try:
        month = date.fromisoformat(raw + "-01") if raw else datetime.now(ZoneInfo("Africa/Kampala")).date().replace(day=1)
    except ValueError:
        return fail("month must use YYYY-MM")
    month_start = month.replace(day=1)
    month_end = date(month_start.year, month_start.month, calendar.monthrange(month_start.year, month_start.month)[1])
    billed, applied, invoice_count = db.session.query(
        func.coalesce(func.sum(Invoice.total_ugx), 0),
        func.coalesce(func.sum(Invoice.paid_ugx), 0),
        func.count(Invoice.id),
    ).filter(Invoice.period_start >= month_start, Invoice.period_start <= month_end,
             Invoice.status != "VOID").one()
    expenses = db.session.query(func.coalesce(func.sum(Expense.amount_ugx), 0)).filter(
        Expense.incurred_on >= month_start, Expense.incurred_on <= month_end
    ).scalar()
    rooms_total = db.session.query(func.count(Room.id)).filter(Room.status != "ARCHIVED").scalar() or 0
    occupied = db.session.query(func.count(Room.id)).filter(Room.status == "OCCUPIED").scalar() or 0
    return jsonify(
        month=month_start.isoformat(), billed_ugx=int(billed),
        applied_to_invoices_ugx=int(applied), outstanding_on_invoices_ugx=int(billed-applied),
        expenses_in_period_ugx=int(expenses or 0),
        gross_invoice_margin_ugx=int(billed) - int(expenses or 0),
        invoices=int(invoice_count), units=int(rooms_total), occupied_units=int(occupied),
        occupancy_percent=round((occupied/rooms_total)*100, 2) if rooms_total else 0,
        methodology="Invoice cohort balances, not a cashflow or profit and loss statement."
    )

@api.get("/reports/arrears")
@roles("OWNER", "MANAGER", "ACCOUNTANT", "SUPER_ADMIN")
def report_arrears(user):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("Africa/Kampala")).date()
    invoices = db.session.query(Invoice).filter(
        Invoice.due_date < now, Invoice.paid_ugx < Invoice.total_ugx,
        Invoice.status.in_(["ISSUED", "PARTIALLY_PAID", "OVERDUE"])
    ).all()
    buckets = {"1_30_days": 0, "31_60_days": 0, "61_90_days": 0, "over_90_days": 0}
    count = 0
    for invoice in invoices:
        age = (now - invoice.due_date).days
        bucket = "1_30_days" if age <= 30 else "31_60_days" if age <= 60 else "61_90_days" if age <= 90 else "over_90_days"
        buckets[bucket] += invoice.total_ugx - invoice.paid_ugx
        count += 1
    return jsonify(as_of=now.isoformat(), overdue_invoices=count,
                   total_ugx=sum(buckets.values()), ageing_ugx=buckets)

@api.get("/reports/export/invoices.csv")
@roles("OWNER", "ACCOUNTANT", "SUPER_ADMIN")
def export_invoices(user):
    import csv
    import io
    from flask import Response
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["Invoice number", "Tenant reference", "Period start", "Period end",
                     "Due date", "Status", "Billed UGX", "Applied UGX", "Outstanding UGX"])
    records = db.session.query(Invoice).order_by(Invoice.created_at.desc()).limit(5000).all()
    for invoice in records:
        # Invoice numbers and references are server-generated UUIDs/IDs; never export arbitrary
        # tenant-supplied text into CSV without protecting against spreadsheet formulas.
        writer.writerow([invoice.invoice_number, invoice.tenant_id,
                         invoice.period_start.isoformat(), invoice.period_end.isoformat(),
                         invoice.due_date.isoformat(), invoice.status,
                         invoice.total_ugx, invoice.paid_ugx,
                         invoice.total_ugx-invoice.paid_ugx])
    response = Response(stream.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = "attachment; filename=kats-invoices.csv"
    response.headers["Cache-Control"] = "no-store"
    return response


@api.get("/inspections")
@jwt_required()
def inspections_list():
    user = current_user()
    query = db.session.query(Inspection)
    if user.role == "CARETAKER":
        assigned = db.session.query(CaretakerAssignment.room_id).filter_by(
            caretaker_user_id=user.id)
        query = query.filter(Inspection.room_id.in_(assigned))
    elif user.role == "TENANT":
        linked = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if not linked:
            return jsonify(items=[], total=0)
        owned_leases = db.session.query(Lease.id).filter_by(tenant_id=linked)
        query = query.filter(Inspection.lease_id.in_(owned_leases))
    elif user.role not in STAFF:
        abort(403)
    results = list_page(Inspection, query.order_by(Inspection.created_at.desc()))
    return jsonify(items=[
        serialize(item, "id", "lease_id", "room_id", "kind", "condition_notes",
                  "damage_estimate_ugx", "observed_on")
        for item in results.items
    ], total=results.total)

@api.post("/inspections")
@jwt_required()
def create_inspection():
    user = current_user()
    obj = data()
    lease = db.session.get(Lease, required_string(obj, "lease_id"))
    if not lease:
        abort(404)
    if user.role == "CARETAKER":
        ensure_assigned(user, lease.room_id)
    elif user.role not in OPERATIONS:
        abort(403)
    kind = required_string(obj, "kind").upper()
    if kind not in ("MOVE_IN", "MOVE_OUT", "ROUTINE"):
        return fail("Invalid inspection kind")
    if lease.status != "ACTIVE" and kind == "MOVE_OUT":
        return fail("Move-out inspection requires an active lease", 409)
    inspection = Inspection(
        lease_id=lease.id, room_id=lease.room_id,
        inspector_id=user.id, kind=kind,
        condition_notes=required_string(obj, "condition_notes", 3000),
        damage_estimate_ugx=ugx(obj.get("damage_estimate_ugx", 0)),
        observed_on=parse_date(obj.get("observed_on"))
    )
    if inspection.observed_on < lease.start_date:
        return fail("Inspection cannot predate the lease")
    db.session.add(inspection)
    db.session.flush()
    audit(user, "inspection.record", "inspection", inspection.id,
          kind=kind, room_id=lease.room_id)
    db.session.commit()
    return jsonify(inspection=serialize(
        inspection, "id", "lease_id", "room_id", "kind", "observed_on"
    )), 201

@api.post("/leases/<lease_id>/terminate")
@roles("OWNER", "MANAGER", "SUPER_ADMIN")
def terminate_lease(user, lease_id):
    obj = data()
    reason = required_string(obj, "reason", 500)
    lease = db.session.query(Lease).filter_by(id=lease_id).with_for_update().first()
    if not lease:
        abort(404)
    if lease.status == "TERMINATED":
        return jsonify(lease=serialize(lease, "id", "status"))
    if lease.status != "ACTIVE":
        return fail("Only active leases can be terminated", 409)
    move_out = db.session.query(Inspection).filter_by(
        lease_id=lease.id, kind="MOVE_OUT"
    ).order_by(Inspection.created_at.desc()).first()
    if not move_out:
        return fail("A move-out inspection is required before termination", 409)
    room = db.session.query(Room).filter_by(id=lease.room_id).with_for_update().first()
    previous = room.status
    lease.status = "TERMINATED"
    room.status = "CLEANING"
    db.session.add(RoomStateHistory(
        room_id=room.id, old_status=previous, new_status="CLEANING",
        reason="Lease termination: " + reason, actor_id=user.id
    ))
    audit(user, "lease.terminate", "lease", lease.id,
          reason=reason, move_out_inspection_id=move_out.id)
    db.session.commit()
    return jsonify(
        lease=serialize(lease, "id", "status"),
        room=serialize(room, "id", "status"),
        warning="Deposit settlement and any outstanding balance require separate approval."
    )


@api.post("/maintenance/<request_id>/status")
@jwt_required()
def update_maintenance_status(request_id):
    user = current_user()
    obj = data()
    target = required_string(obj, "status").upper()
    reason = required_string(obj, "reason", 500)
    job = db.session.query(MaintenanceRequest).filter_by(id=request_id).with_for_update().first()
    if not job:
        abort(404)
    if user.role == "CARETAKER":
        ensure_assigned(user, job.room_id)
        if target not in ("IN_PROGRESS", "ON_HOLD"):
            abort(403)
    elif user.role not in OPERATIONS:
        abort(403)
    transitions = {
        "OPEN": {"ASSIGNED", "IN_PROGRESS", "REJECTED", "CANCELLED"},
        "ASSIGNED": {"IN_PROGRESS", "ON_HOLD", "CANCELLED"},
        "IN_PROGRESS": {"COMPLETED", "ON_HOLD"},
        "ON_HOLD": {"IN_PROGRESS", "CANCELLED"},
        "COMPLETED": {"OPEN"},
        "REJECTED": {"OPEN"},
        "CANCELLED": {"OPEN"},
    }
    if target == job.status:
        return jsonify(request=serialize(job, "id", "status"))
    if target not in transitions.get(job.status, set()):
        return fail("Invalid maintenance status transition", 409)
    previous = job.status
    job.status = target
    audit(user, "maintenance.status", "maintenance", job.id,
          previous=previous, new=target, reason=reason)
    db.session.commit()
    return jsonify(request=serialize(job, "id", "status"))

@api.get("/receipts")
@jwt_required()
def receipts():
    user = current_user()
    query = db.session.query(Payment).join(Invoice, Payment.invoice_id == Invoice.id).filter(
        Payment.status.in_(["RECONCILED", "REVERSED"]))
    if user.role == "TENANT":
        tenant_id = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if not tenant_id:
            return jsonify(items=[], total=0)
        query = query.filter(Invoice.tenant_id == tenant_id)
    elif user.role == "CARETAKER":
        query = query.filter(Payment.created_by == user.id)
    elif user.role not in STAFF:
        abort(403)
    results = list_page(Payment, query.order_by(Payment.created_at.desc()))
    return jsonify(items=[
        dict(receipt_number="KATS-REC-" + p.id[:12].upper(),
             payment_id=p.id, invoice_id=p.invoice_id,
             amount_ugx=p.amount_ugx,
             valid=p.status == "RECONCILED", fiscal_status="NOT_FISCALIZED")
        for p in results.items
    ], total=results.total)

@api.get("/receipts/<payment_id>")
@jwt_required()
def receipt_detail(payment_id):
    user = current_user()
    payment = db.session.get(Payment, payment_id)
    if not payment or payment.status not in ("RECONCILED", "REVERSED"):
        abort(404)
    invoice = db.session.get(Invoice, payment.invoice_id)
    if user.role == "TENANT":
        linked = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if linked is None or invoice.tenant_id != linked:
            abort(404)
    elif user.role == "CARETAKER":
        if payment.created_by != user.id:
            abort(404)
    elif user.role not in STAFF:
        abort(403)
    return jsonify(
        receipt_number="KATS-REC-" + payment.id[:12].upper(),
        payment_id=payment.id, invoice_number=invoice.invoice_number,
        amount_ugx=payment.amount_ugx, method=payment.method,
        recorded_at=payment.created_at.isoformat(),
        valid=payment.status == "RECONCILED", fiscal_status="NOT_FISCALIZED",
        notice="Internal payment acknowledgement only. Not a URA EFRIS fiscal receipt or proof of a bank transfer."
    )
