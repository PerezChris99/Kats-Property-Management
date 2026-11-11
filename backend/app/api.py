from datetime import date, datetime, timezone, timedelta
import unicodedata
from functools import wraps
import os
from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token, get_jwt_identity, get_jwt, decode_token,
    jwt_required, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
)
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from sqlalchemy import func, case
from sqlalchemy.exc import IntegrityError
from .extensions import db, limiter
from .models import (
    User, RefreshSession, Permission, Role, RolePermission, Property, Building, Floor, Room, RoomStateHistory, Tenant, Lease,
    Invoice, InvoiceLine, CreditNote, Payment, LedgerEntry, MaintenanceRequest, Expense, ExpenseEvent, AuditLog, CaretakerAssignment, Inspection
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
    # Bound nested structured input so attackers cannot exhaust CPU/DB memory
    # with oversized array/map allocations. Preserve literal HTML as inert
    # text: escaping belongs to the display context, never SQL concatenation.
    remaining = [5000]
    def validate(item, depth=0):
        remaining[0] -= 1
        if remaining[0] < 0 or depth > 12:
            abort(400, description="JSON structure is too complex")
        if isinstance(item, str):
            if len(item) > 100000 or any(
                (unicodedata.category(ch) in ("Cc", "Cs") and ch not in ("\n", "\t"))
                or unicodedata.bidirectional(ch) in ("RLO", "LRO", "RLE", "LRE", "PDF")
                for ch in item
            ):
                abort(400, description="Invalid text or control characters")
        elif isinstance(item, dict):
            if len(item) > 100:
                abort(400, description="Too many JSON object fields")
            for key, child in item.items():
                if not isinstance(key, str) or len(key) > 120:
                    abort(400, description="Invalid JSON field name")
                validate(child, depth + 1)
        elif isinstance(item, list):
            if len(item) > 1000:
                abort(400, description="Too many JSON list items")
            for child in item:
                validate(child, depth + 1)
    validate(value)
    return value

def required_string(obj, key, max_length=250):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        abort(400, description=key + " is required and must be text")
    # Reject control bytes and text-direction overrides. React escapes text;
    # do not run a lossy HTML sanitizer on legitimate literal descriptions.
    if any((unicodedata.category(ch) in ("Cc", "Cs") and ch not in ("\n", "\t")) or
           unicodedata.bidirectional(ch) in ("RLO", "LRO", "RLE", "LRE", "PDF") for ch in value):
        abort(400, description=key + " contains forbidden control characters")
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
    """Enforce statutory app ceiling plus mutable DB role grants.

    Each decorated route has a role permission seeded by the CLI. Once a route
    permission exists, revocation takes effect without redeployment.
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args, **kwargs):
            user = current_user()
            if user.role not in allowed:
                abort(403)
            permission_name = "route:" + str(request.endpoint)
            rule = db.session.get(Permission, permission_name)
            if rule is None:
                if os.getenv("APP_ENV") == "production":
                    abort(403, description="Permission registry not initialized")
            elif not db.session.get(RolePermission,(user.role, permission_name)):
                abort(403, description="Role permission revoked")
            return fn(user, *args, **kwargs)
        wrapped.__allowed_roles__ = tuple(allowed)
        return wrapped
    return decorator

def list_page(model, query):
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("page_size", 25))
    except (TypeError, ValueError):
        abort(400, description="Invalid pagination parameters")
    if not 1 <= page <= 200 or not 1 <= size <= 100 or (page - 1) * size > 10000:
        abort(400, description="Pagination exceeds bounded offset; narrow the query")
    count = request.args.get("include_total", "1") != "0"
    return query.paginate(page=page, per_page=size, error_out=False, count=count)

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
    if user.mfa_enabled:
        from .mfa import decrypt_secret, verify_totp_code, MfaUnavailable
        # Lock the user record so one 30-second TOTP step cannot be replayed
        # across concurrent logins or multiple web workers.
        user = db.session.query(User).filter_by(id=user.id).with_for_update().one()
        code = obj.get("mfa_code")
        if not isinstance(code, str) or not code.isdecimal() or len(code) != 6:
            return fail("Valid authenticator code required", 401)
        try:
            matched = verify_totp_code(decrypt_secret(user.mfa_secret_encrypted), code)
        except MfaUnavailable:
            return fail("Two-factor verifier unavailable", 503)
        if matched is None or (user.mfa_last_step is not None and matched <= user.mfa_last_step):
            return fail("Invalid or previously used authenticator code", 401)
        user.mfa_last_step = matched
    return _issue_login_session(user)


def _issue_login_session(user, *, event="auth.login"):
    """Normal audited, revocable JWT cookie login for password and demo flows."""
    response = jsonify(user=serialize(user, "id", "full_name", "role"))
    claims = {"sv": user.session_version}
    refresh_token = create_refresh_token(identity=user.id, additional_claims=claims)
    expiry = datetime.fromtimestamp(decode_token(refresh_token)["exp"], tz=timezone.utc)
    db.session.add(RefreshSession(user_id=user.id, token_jti=decode_token(refresh_token)["jti"], expires_at=expiry))
    audit(user, event, "user", user.id)
    db.session.commit()
    set_access_cookies(response, create_access_token(identity=user.id, additional_claims=claims))
    set_refresh_cookies(response, refresh_token)
    return response


@api.get("/auth/demo-accounts")
@limiter.limit("30 per minute")
def demo_accounts():
    from .demo_preview import demo_http_allowed
    if not demo_http_allowed():
        abort(404)
    from .models import User
    accounts = []
    for key, email in [("landlord", "landlord@demo.kats.invalid")] + [
        (f"tenant-{i:02d}", f"tenant{i:02d}@demo.kats.invalid") for i in range(1, 31)
    ]:
        account = db.session.query(User).filter_by(email=email, is_active=True).first()
        if account and account.role == ("OWNER" if key == "landlord" else "TENANT"):
            accounts.append({"key": key, "name": account.full_name,
                             "role": "LANDLORD" if key == "landlord" else "TENANT"})
    # An unseeded preview never displays non-functional shortcuts.
    if len(accounts) != 31:
        return jsonify(enabled=False, accounts=[])
    return jsonify(enabled=True, accounts=accounts)


@api.post("/auth/demo-sign-in")
@limiter.limit("60 per minute")
def demo_sign_in():
    from .demo_preview import demo_http_allowed
    if not demo_http_allowed():
        abort(404)
    obj = data()
    key = obj.get("account")
    if key == "landlord":
        email, role = "landlord@demo.kats.invalid", "OWNER"
    elif isinstance(key, str) and len(key) == 9 and key.startswith("tenant-") and key[-2:].isdigit() and 1 <= int(key[-2:]) <= 30:
        email, role = f"tenant{key[-2:]}@demo.kats.invalid", "TENANT"
    else:
        return fail("Unknown demo account", 400)
    user = db.session.query(User).filter_by(email=email, role=role, is_active=True).first()
    if user is None or user.mfa_enabled:
        return fail("Demo account is unavailable. Run preview setup.", 404)
    if role == "TENANT" and not db.session.query(Tenant.id).filter_by(user_id=user.id).first():
        return fail("Demo tenant has no linked rental profile.", 404)
    return _issue_login_session(user, event="auth.demo_login")

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
    query=db.session.query(Property)
    query_text=request.args.get("q","").strip()
    if len(query_text)>100:
        return fail("Search term too long")
    if query_text:
        from sqlalchemy import or_
        escaped=query_text.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
        term="%"+escaped+"%"
        query=query.filter(or_(Property.name.ilike(term,escape="\\"),
                              Property.address.ilike(term,escape="\\"),
                              Property.district.ilike(term,escape="\\")))
    results = list_page(Property, query.order_by(Property.name))
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
    if request.args.get("floor_id"):
        query = query.filter_by(floor_id=request.args["floor_id"])
    if request.args.get("status"):
        if request.args["status"] not in ROOM_STATES:
            return fail("Unknown room state")
        query=query.filter_by(status=request.args["status"])
    query_text=request.args.get("q","").strip()
    if len(query_text)>60:
        return fail("Search term too long")
    if query_text:
        escaped=query_text.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
        query=query.filter(Room.number.ilike("%"+escaped+"%",escape="\\"))
    results = list_page(Room, query.order_by(Room.number))
    return jsonify(items=[serialize(r, "id", "property_id", "floor_id", "number", "status", "rent_ugx", "deposit_ugx") for r in results.items], total=results.total)

@api.post("/rooms")
@roles(*OPERATIONS)
def add_room(user):
    obj = data()
    property_id = required_string(obj, "property_id")
    if not db.session.get(Property, property_id):
        abort(404)
    floor_id = obj.get("floor_id")
    if floor_id:
        floor = db.session.get(Floor, floor_id)
        if not floor or db.session.get(Building, floor.building_id).property_id != property_id:
            return fail("Selected floor does not belong to this property", 409)
    room = Room(property_id=property_id, floor_id=floor_id or None,
                number=required_string(obj, "number", 60),
                rent_ugx=ugx(obj.get("rent_ugx")),
                deposit_ugx=ugx(obj.get("deposit_ugx", 0)))
    db.session.add(room)
    try:
        db.session.flush()
        audit(user, "room.create", "room", room.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Room number already exists for the property", 409)
    return jsonify(room=serialize(room, "id", "number", "status", "rent_ugx", "property_id", "floor_id")), 201

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
    rent_amount = ugx(obj.get("rent_ugx"), positive=True)
    deposit_amount = ugx(obj.get("deposit_ugx", 0))
    if deposit_amount > rent_amount:
        return fail("Security deposit cannot exceed one month's rent (Landlord and Tenant Act section 30)", 409)
    lease = Lease(room_id=room.id, tenant_id=tenant.id, start_date=start, end_date=end,
                  rent_ugx=rent_amount, deposit_ugx=deposit_amount,
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
    fields = ("id", "invoice_number", "lease_id", "tenant_id", "period_start", "period_end", "due_date", "total_ugx", "paid_ugx", "credit_ugx", "status")
    return jsonify(items=[serialize(inv, *fields) for inv in results.items], total=results.total)

@api.post("/invoices")
@roles(*STAFF)
def add_invoice(user):
    obj = data()
    # Serialize all manual rent issuance with proration and the scheduler.
    lease = db.session.query(Lease).filter_by(id=required_string(obj, "lease_id")).with_for_update().first()
    if not lease or lease.status != "ACTIVE":
        return fail("Active lease required")
    start, end, due = [parse_date(obj.get(key)) for key in ("period_start", "period_end", "due_date")]
    if end < start or start < lease.start_date or end > lease.end_date:
        return fail("Billing period outside lease bounds")
    supplied_lines = obj.get("lines")
    prepared = []
    if supplied_lines is not None:
        if not isinstance(supplied_lines, list) or not 1 <= len(supplied_lines) <= 30:
            return fail("Invoice must contain between one and thirty lines")
        for line in supplied_lines:
            if not isinstance(line, dict):
                return fail("Invoice line must be an object")
            quantity = line.get("quantity", 1)
            if type(quantity) is not int or not 1 <= quantity <= 100000:
                return fail("Line quantity must be a positive integer")
            price = ugx(line.get("unit_price_ugx"))
            kind = required_string(line, "charge_type", 40).upper()
            if kind not in {"RENT","WATER","ELECTRICITY","GARBAGE","PARKING","CLEANING","DAMAGE","LATE_FEE","MISCELLANEOUS"}:
                return fail("Unsupported invoice charge type")
            description = required_string(line, "description", 300)
            amount = quantity * price
            if amount > 10**15:
                return fail("Invoice line amount exceeds allowable limit")
            prepared.append((kind, description, quantity, price, amount))
        total = sum(entry[4] for entry in prepared)
        ugx(total, positive=True)
        if "total_ugx" in obj and ugx(obj["total_ugx"]) != total:
            return fail("Invoice total must equal the sum of its lines")
    else:
        total = ugx(obj.get("total_ugx"), positive=True)
        prepared = [("RENT", "Rent and approved charges", 1, total, total)]
    if any(line[0] == "RENT" for line in prepared):
        overlap = (db.session.query(Invoice.id)
                   .join(InvoiceLine, InvoiceLine.invoice_id == Invoice.id)
                   .filter(Invoice.lease_id == lease.id, Invoice.status != "VOID",
                           Invoice.period_start <= end, Invoice.period_end >= start,
                           InvoiceLine.charge_type == "RENT").first())
        if overlap:
            return fail("Rent is already invoiced for an overlapping period", 409)
    from .models import new_id
    invoice = Invoice(lease_id=lease.id, tenant_id=lease.tenant_id, period_start=start, period_end=end,
                      due_date=due, total_ugx=total, invoice_number="KATS-" + new_id()[:12].upper())
    db.session.add(invoice)
    try:
        db.session.flush()
        db.session.add_all([
            InvoiceLine(invoice_id=invoice.id, charge_type=kind, description=description,
                        quantity=qty, unit_price_ugx=price, amount_ugx=amount)
            for kind, description, qty, price, amount in prepared
        ])
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
    if not invoice or invoice.status in ("VOID", "PAID", "CREDITED"):
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
    if amount > invoice.total_ugx - invoice.credit_ugx - invoice.paid_ugx:
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
    if invoice.status == "VOID" or payment.amount_ugx > invoice.total_ugx - invoice.credit_ugx - invoice.paid_ugx:
        return fail("Payment conflicts with current invoice balance", 409)
    invoice.paid_ugx += payment.amount_ugx
    invoice.status = "PAID" if invoice.paid_ugx + invoice.credit_ugx == invoice.total_ugx else "PARTIALLY_PAID"
    payment.status = "RECONCILED"
    payment.settled_at = datetime.now(timezone.utc)
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
    return jsonify(items=[serialize(e, "id", "property_id", "category", "description",
                                   "amount_ugx", "incurred_on", "status", "created_by",
                                   "reviewed_by") for e in results.items], total=results.total)

@api.post("/expenses")
@roles(*STAFF)
def add_expense(user):
    obj = data()
    prop = db.session.get(Property, required_string(obj, "property_id"))
    if not prop:
        abort(404)
    category=required_string(obj,"category",80)
    description=required_string(obj,"description",500)
    amount=ugx(obj.get("amount_ugx"),positive=True)
    incurred=parse_date(obj.get("incurred_on"))
    key=required_string(obj,"idempotency_key",128)
    existing=db.session.query(Expense).filter_by(idempotency_key=key).first()
    if existing:
        if (existing.created_by!=user.id or existing.property_id!=prop.id or
                existing.category!=category or existing.description!=description or
                existing.amount_ugx!=amount or existing.incurred_on!=incurred):
            return fail("Expense idempotency key was reused with different data",409)
        return jsonify(expense=serialize(existing,"id","amount_ugx","status")),200
    expense = Expense(property_id=prop.id, category=category, description=description,
                      amount_ugx=amount, incurred_on=incurred,created_by=user.id,
                      idempotency_key=key,status="PENDING_APPROVAL")
    db.session.add(expense)
    try:
        db.session.flush()
        db.session.add(ExpenseEvent(expense_id=expense.id,event="RECORDED",
                                    amount_ugx=0,actor_id=user.id,reason="Awaiting independent review"))
        audit(user, "expense.record", "expense", expense.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Expense command already submitted",409)
    return jsonify(expense=serialize(expense, "id", "amount_ugx","status")), 201

@api.post("/expenses/<expense_id>/review")
@roles("OWNER","ACCOUNTANT","SUPER_ADMIN")
def review_expense(user,expense_id):
    obj=data()
    decision=required_string(obj,"decision",20).upper()
    reason=required_string(obj,"reason",500)
    if decision not in ("APPROVE","REJECT"):
        return fail("Decision must be APPROVE or REJECT")
    expense=db.session.query(Expense).filter_by(id=expense_id).with_for_update().first()
    if not expense:
        abort(404)
    if expense.status not in ("PENDING_APPROVAL","REVIEW_REQUIRED"):
        return fail("Expense has already been reviewed",409)
    if expense.created_by==user.id:
        return fail("Expense must be reviewed by a different authorized user",403)
    expense.status="APPROVED" if decision=="APPROVE" else "REJECTED"
    expense.reviewed_by=user.id
    expense.reviewed_at=datetime.now(timezone.utc)
    db.session.add(ExpenseEvent(expense_id=expense.id,
        event="APPROVED" if decision=="APPROVE" else "REJECTED",
        amount_ugx=expense.amount_ugx if decision=="APPROVE" else 0,
        actor_id=user.id,reason=reason))
    audit(user,"expense.review","expense",expense.id,decision=decision,reason=reason)
    db.session.commit()
    return jsonify(expense=serialize(expense,"id","amount_ugx","status","reviewed_by"),
                   notice="Approved accounting cost, not proof of cash disbursement")

@api.post("/expenses/<expense_id>/reverse")
@roles("OWNER","SUPER_ADMIN")
def reverse_expense(user,expense_id):
    reason=required_string(data(),"reason",500)
    expense=db.session.query(Expense).filter_by(id=expense_id).with_for_update().first()
    if not expense:
        abort(404)
    if expense.status=="REVERSED":
        return jsonify(expense=serialize(expense,"id","status"))
    if expense.status!="APPROVED":
        return fail("Only approved expenses can be reversed",409)
    if expense.reviewed_by==user.id:
        return fail("An approved expense must be reversed by a different reviewer",403)
    expense.status="REVERSED"
    expense.reversal_reason=reason
    db.session.add(ExpenseEvent(expense_id=expense.id,event="REVERSED",
                                amount_ugx=-expense.amount_ugx,
                                actor_id=user.id,reason=reason))
    audit(user,"expense.reverse","expense",expense.id,reason=reason)
    db.session.commit()
    return jsonify(expense=serialize(expense,"id","status"),
                   notice="Accounting reversal recorded; no bank/payment-provider refund initiated")

@api.get("/expenses/<expense_id>/events")
@roles(*STAFF)
def expense_events(user,expense_id):
    expense=db.session.get(Expense,expense_id)
    if not expense:
        abort(404)
    events=db.session.query(ExpenseEvent).filter_by(expense_id=expense_id).order_by(
        ExpenseEvent.created_at).all()
    return jsonify(items=[serialize(e,"id","event","amount_ugx","actor_id",
                                    "reason","created_at") for e in events])

@api.get("/dashboard")
@roles(*STAFF)
def dashboard(user):
    rooms_count = db.session.query(func.count(Room.id)).filter(Room.status != "ARCHIVED").scalar() or 0
    occupied = db.session.query(func.count(Room.id)).filter(Room.status == "OCCUPIED").scalar() or 0
    actually_vacant = db.session.query(func.count(Room.id)).filter(Room.status == "VACANT").scalar() or 0
    reserved = db.session.query(func.count(Room.id)).filter(Room.status == "RESERVED").scalar() or 0
    unavailable = db.session.query(func.count(Room.id)).filter(Room.status.in_(("MAINTENANCE", "UNAVAILABLE", "DISPUTE"))).scalar() or 0
    expected = db.session.query(func.coalesce(func.sum(Invoice.total_ugx - Invoice.credit_ugx), 0)).filter(Invoice.status != "VOID").scalar() or 0
    paid = db.session.query(func.coalesce(func.sum(Invoice.paid_ugx), 0)).filter(Invoice.status != "VOID").scalar() or 0
    open_maintenance = db.session.query(func.count(MaintenanceRequest.id)).filter(MaintenanceRequest.status.in_(["OPEN","ASSIGNED","IN_PROGRESS","ON_HOLD"])).scalar() or 0
    return jsonify(rooms=rooms_count, occupied_rooms=occupied, vacant_rooms=actually_vacant,
                   reserved_rooms=reserved, unavailable_rooms=unavailable,
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
    details = serialize(lease, "id", "tenant_id", "room_id", "start_date", "end_date",
                        "rent_ugx", "deposit_ugx", "due_day", "status")
    room = db.session.get(Room, lease.room_id)
    if room:
        details["room_number"] = room.number
        property_ = db.session.get(Property, room.property_id)
        if property_:
            details["property_name"] = property_.name
    return jsonify(lease=details)

@api.get("/tenant/dashboard")
@roles("TENANT")
def tenant_dashboard(user):
    tenant_id = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
    if not tenant_id:
        return jsonify(total_ugx=0, paid_ugx=0, outstanding_ugx=0, invoices=0)
    total, paid, credited, count = db.session.query(
        func.coalesce(func.sum(Invoice.total_ugx), 0),
        func.coalesce(func.sum(Invoice.paid_ugx), 0),
        func.coalesce(func.sum(Invoice.credit_ugx), 0),
        func.count(Invoice.id)
    ).filter(Invoice.tenant_id == tenant_id, Invoice.status != "VOID").one()
    return jsonify(total_ugx=int(total), paid_ugx=int(paid),
                   credited_ugx=int(credited),
                   outstanding_ugx=int(total - paid - credited), invoices=int(count))


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
    if not invoice or invoice.status in ("PAID", "VOID", "CREDITED"):
        return fail("Open invoice required")
    lease = db.session.get(Lease, invoice.lease_id)
    ensure_assigned(user, lease.room_id)
    amount = ugx(obj.get("amount_ugx"), positive=True)
    if amount > invoice.total_ugx - invoice.credit_ugx - invoice.paid_ugx:
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
    if os.getenv("APP_ENV") == "production":
        return fail("Password-based staff provisioning is disabled. Use secure invitations.", 403)
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
    invoice.status = ("PAID" if invoice.paid_ugx and invoice.paid_ugx + invoice.credit_ugx == invoice.total_ugx
                      else "CREDITED" if invoice.credit_ugx == invoice.total_ugx
                      else "ISSUED" if invoice.paid_ugx == 0 else "PARTIALLY_PAID")
    payment.status = "REVERSED"
    payment.reversed_at = datetime.now(timezone.utc)
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
    if invoice.paid_ugx != 0 or invoice.credit_ugx != 0:
        return fail("Invoices with payments or credits cannot be voided", 409)
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
    billed, credited, applied, invoice_count = db.session.query(
        func.coalesce(func.sum(Invoice.total_ugx), 0),
        func.coalesce(func.sum(Invoice.credit_ugx), 0),
        func.coalesce(func.sum(Invoice.paid_ugx), 0),
        func.count(Invoice.id),
    ).filter(Invoice.period_start >= month_start, Invoice.period_start <= month_end,
             Invoice.status != "VOID").one()
    expenses = db.session.query(func.coalesce(func.sum(Expense.amount_ugx), 0)).filter(
        Expense.incurred_on >= month_start, Expense.incurred_on <= month_end,
        Expense.status == "APPROVED"
    ).scalar()
    rooms_total = db.session.query(func.count(Room.id)).filter(Room.status != "ARCHIVED").scalar() or 0
    occupied = db.session.query(func.count(Room.id)).filter(Room.status == "OCCUPIED").scalar() or 0
    return jsonify(
        month=month_start.isoformat(), billed_ugx=int(billed),
        credited_ugx=int(credited), net_billed_ugx=int(billed - credited),
        applied_to_invoices_ugx=int(applied), outstanding_on_invoices_ugx=int(billed-credited-applied),
        expenses_in_period_ugx=int(expenses or 0),
        gross_invoice_margin_ugx=int(billed - credited) - int(expenses or 0),
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
    # SQL GROUP BY avoids loading every arrears invoice into Python memory.
    bucket = case(
        (Invoice.due_date >= now - timedelta(days=30), "1_30_days"),
        (Invoice.due_date >= now - timedelta(days=60), "31_60_days"),
        (Invoice.due_date >= now - timedelta(days=90), "61_90_days"),
        else_="over_90_days",
    )
    amounts = db.session.query(bucket.label("age_bucket"),
        func.count(Invoice.id),
        func.sum(Invoice.total_ugx - Invoice.credit_ugx - Invoice.paid_ugx)
    ).filter(
        Invoice.due_date < now,
        Invoice.paid_ugx + Invoice.credit_ugx < Invoice.total_ugx,
        Invoice.status.in_(["ISSUED", "PARTIALLY_PAID", "OVERDUE"])
    ).group_by(bucket).all()
    buckets = {"1_30_days": 0, "31_60_days": 0, "61_90_days": 0, "over_90_days": 0}
    count = 0
    for key, rows, outstanding in amounts:
        buckets[key] = int(outstanding)
        count += rows
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
                     "Due date", "Status", "Billed UGX", "Credited UGX", "Applied UGX", "Outstanding UGX"])
    records = db.session.query(Invoice).order_by(Invoice.created_at.desc()).limit(5000).all()
    for invoice in records:
        # Invoice numbers and references are server-generated UUIDs/IDs; never export arbitrary
        # tenant-supplied text into CSV without protecting against spreadsheet formulas.
        writer.writerow([invoice.invoice_number, invoice.tenant_id,
                         invoice.period_start.isoformat(), invoice.period_end.isoformat(),
                         invoice.due_date.isoformat(), invoice.status,
                         invoice.total_ugx, invoice.credit_ugx, invoice.paid_ugx,
                         invoice.total_ugx-invoice.credit_ugx-invoice.paid_ugx])
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


@api.get("/invoices/<invoice_id>/lines")
@jwt_required()
def invoice_lines(invoice_id):
    user = current_user()
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        abort(404)
    if user.role == "TENANT":
        owned = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if invoice.tenant_id != owned:
            abort(404)
    elif user.role not in STAFF:
        abort(403)
    rows = db.session.query(InvoiceLine).filter_by(invoice_id=invoice.id).all()
    return jsonify(items=[serialize(x, "id", "description", "charge_type", "quantity",
                                    "unit_price_ugx", "amount_ugx") for x in rows])

@api.get("/invoices/<invoice_id>/credit-notes")
@jwt_required()
def list_invoice_credits(invoice_id):
    user = current_user()
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        abort(404)
    if user.role == "TENANT":
        linked = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if linked is None or invoice.tenant_id != linked:
            abort(404)
    elif user.role not in STAFF:
        abort(403)
    credits = db.session.query(CreditNote).filter_by(invoice_id=invoice.id).order_by(CreditNote.created_at).all()
    return jsonify(items=[serialize(x, "id", "amount_ugx", "reason", "created_at") for x in credits])

@api.post("/invoices/<invoice_id>/credit-notes")
@roles("OWNER", "ACCOUNTANT", "SUPER_ADMIN")
def apply_invoice_credit(user, invoice_id):
    obj = data()
    amount = ugx(obj.get("amount_ugx"), positive=True)
    key = required_string(obj, "idempotency_key", 128)
    reason = required_string(obj, "reason", 500)
    existing = db.session.query(CreditNote).filter_by(idempotency_key=key).first()
    if existing:
        if existing.invoice_id != invoice_id or existing.amount_ugx != amount:
            return fail("Conflicting idempotency key", 409)
        return jsonify(credit=serialize(existing, "id", "invoice_id", "amount_ugx")), 200
    invoice = db.session.query(Invoice).filter_by(id=invoice_id).with_for_update().first()
    if not invoice:
        abort(404)
    if invoice.status == "VOID" or amount > invoice.total_ugx - invoice.credit_ugx - invoice.paid_ugx:
        return fail("Credit exceeds outstanding balance or invoice is void", 409)
    note = CreditNote(invoice_id=invoice.id, amount_ugx=amount, reason=reason,
                      created_by=user.id, idempotency_key=key)
    invoice.credit_ugx += amount
    if invoice.paid_ugx + invoice.credit_ugx == invoice.total_ugx:
        invoice.status = "PAID" if invoice.paid_ugx > 0 else "CREDITED"
    else:
        invoice.status = "PARTIALLY_PAID" if invoice.paid_ugx else "ISSUED"
    db.session.add(note)
    try:
        db.session.flush()
        db.session.add(LedgerEntry(invoice_id=invoice.id, event="CREDIT_NOTE_ISSUED",
                                   amount_ugx=-amount))
        audit(user, "invoice.credit_note", "invoice", invoice.id,
              credit_note_id=note.id, amount_ugx=amount, reason=reason)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Duplicate credit note", 409)
    return jsonify(credit=serialize(note, "id", "invoice_id", "amount_ugx"),
                   invoice=serialize(invoice, "id", "total_ugx", "credit_ugx", "paid_ugx", "status")), 201


@api.get("/tenant/profile")
@roles("TENANT")
def tenant_profile(user):
    tenant = db.session.query(Tenant).filter_by(user_id=user.id).first()
    if not tenant:
        return jsonify(tenant=None)
    return jsonify(tenant=serialize(tenant, "id", "full_name", "phone", "email"))


@api.get("/admin/permissions")
@roles("OWNER","SUPER_ADMIN")
def list_permission_matrix(user):
    permissions=db.session.query(Permission).order_by(Permission.name).all()
    grants=db.session.query(RolePermission).all()
    by_permission={}
    for g in grants:
        by_permission.setdefault(g.permission_name,[]).append(g.role_name)
    return jsonify(items=[{"name":p.name,"description":p.description,
                           "granted_roles":sorted(by_permission.get(p.name,[]))}
                          for p in permissions])

@api.put("/admin/permissions/<path:name>/roles/<role>")
@roles("SUPER_ADMIN")
def update_permission_grant(user,name,role):
    if role not in {"OWNER","MANAGER","ACCOUNTANT","CARETAKER","TENANT","SUPER_ADMIN"}:
        return fail("Invalid role")
    rule=db.session.get(Permission,name)
    if not rule:
        abort(404)
    # Core super-admin management and auth must never be lockable via this endpoint.
    if name.endswith("admin_permission_grant") or name.endswith("update_permission_grant"):
        return fail("Permission management cannot be disabled",403)
    desired=data().get("allowed")
    if type(desired) is not bool:
        return fail("allowed must be a boolean")
    rule_endpoint=name.removeprefix("route:")
    from flask import current_app
    view=current_app.view_functions.get(rule_endpoint)
    if view is None:
        return fail("Unknown permission endpoint")
    ceiling=getattr(view,"__allowed_roles__",())
    if role not in ceiling and desired:
        return fail("Role cannot exceed the route security ceiling",403)
    grant=db.session.get(RolePermission,(role,name))
    if desired and not grant:
        db.session.add(RolePermission(role_name=role,permission_name=name))
    elif not desired and grant:
        db.session.delete(grant)
    audit(user,"permission.update","permission",user.id,permission=name,role=role,allowed=desired)
    db.session.commit()
    return jsonify(permission=name,role=role,allowed=desired)


@api.get("/tenant/rooms")
@roles("TENANT")
def tenant_rooms(user):
    linked=db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
    if linked is None:
        return jsonify(items=[],total=0)
    leases=db.session.query(Lease).filter_by(tenant_id=linked,status="ACTIVE").all()
    ids=[lease.room_id for lease in leases]
    rooms=db.session.query(Room).filter(Room.id.in_(ids)).all()
    return jsonify(items=[serialize(r,"id","number","property_id","status") for r in rooms],
                   total=len(rooms))

@api.get("/caretaker/roster")
@roles("OWNER","MANAGER","SUPER_ADMIN")
def caretaker_roster(user):
    rows=db.session.query(User).filter_by(role="CARETAKER",is_active=True).order_by(
        User.full_name).limit(500).all()
    return jsonify(items=[serialize(u,"id","full_name","role") for u in rows],total=len(rows))

@api.get("/tenants/accounts")
@roles("OWNER","MANAGER","SUPER_ADMIN")
def available_tenant_accounts(user):
    linked=db.session.query(Tenant.user_id).filter(Tenant.user_id.isnot(None))
    rows=db.session.query(User).filter(User.role=="TENANT",User.is_active.is_(True),
                                    ~User.id.in_(linked)).order_by(User.full_name).limit(500).all()
    return jsonify(items=[serialize(u,"id","full_name","email") for u in rows],total=len(rows))
