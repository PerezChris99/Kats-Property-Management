"""Account-scoped payment initiation and independent transaction verification."""
import os
import re
import uuid
from flask import Blueprint, abort, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from .api import current_user, data, required_string, ugx, fail, serialize, audit
from .extensions import db, limiter
from .models import Invoice, Tenant, Payment
from .extra_models import ProviderAttempt
from .providers import provider, ProviderError
from .settlement import verify_and_post, SettlementError

mobile_api = Blueprint("mobile_payments", __name__)
PROVIDERS = {"MTN_MOMO","AIRTEL_MONEY"}
ALLOWED_STAFF = {"OWNER","MANAGER","ACCOUNTANT","SUPER_ADMIN"}

def visible_invoice(user, invoice):
    if not invoice:
        abort(404)
    if user.role == "TENANT":
        linked = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if linked is None or invoice.tenant_id != linked:
            abort(404)
    elif user.role not in ALLOWED_STAFF:
        abort(403)
    return invoice

@mobile_api.post("/payments/mobile/initiate")
@jwt_required()
@limiter.limit("8 per minute")
def initiate_mobile_payment():
    user = current_user()
    obj = data()
    name = required_string(obj, "provider", 30).upper()
    if name not in PROVIDERS:
        return fail("Unsupported mobile money network")
    if os.getenv(name+"_ENABLED", "false").lower() != "true":
        return fail("Mobile money provider is not activated", 503)
    try:
        client = provider(name)
    except ProviderError:
        return fail("Mobile money provider configuration is incomplete", 503)
    key = required_string(obj, "idempotency_key", 128)
    amount = ugx(obj.get("amount_ugx"), positive=True)
    phone = required_string(obj, "msisdn", 20).replace("+","")
    if not re.fullmatch(r"256[37]\d{8}", phone):
        return fail("Enter a valid Ugandan mobile-money number (256...)")
    invoice = visible_invoice(user, db.session.get(Invoice, required_string(obj, "invoice_id")))
    existing = db.session.query(Payment).filter_by(idempotency_key=key).first()
    if existing:
        if (existing.created_by != user.id or existing.invoice_id != invoice.id or
                existing.amount_ugx != amount or existing.method != name):
            return fail("Idempotency key reused with different transaction details", 409)
        return jsonify(payment=serialize(existing,"id","status","amount_ugx"),reused=True), 200
    if invoice.status in ("PAID","CREDITED","VOID") or amount > invoice.total_ugx - invoice.credit_ugx - invoice.paid_ugx:
        return fail("Invoice does not have enough outstanding balance", 409)
    reference = str(uuid.uuid4())
    payment = Payment(invoice_id=invoice.id, amount_ugx=amount, method=name,
                      status="INITIATED", idempotency_key=key, created_by=user.id)
    db.session.add(payment)
    db.session.flush()
    attempt = ProviderAttempt(payment_id=payment.id, provider=name, reference=reference,
                              requested_amount_ugx=amount, msisdn=phone, status="INITIATED")
    db.session.add(attempt)
    try:
        audit(user,"provider.payment_initiated","payment",payment.id,network=name)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Duplicate payment command",409)
    # Request may time out after the provider accepts it. Preserve pending state
    # and reconcile by status query; never initiate a second charge on retry.
    error = None
    try:
        client.initiate(reference, amount, phone, invoice.invoice_number)
        attempt.status = "PENDING"
    except ProviderError:
        attempt.status = "RETRYING"
        attempt.last_error_code = "INITIATION_UNKNOWN"
        error = "Provider response unconfirmed. Check status before attempting another payment."
    payment.status = "PENDING_PROVIDER"
    db.session.commit()
    return jsonify(payment=serialize(payment,"id","status","amount_ugx","method"),
                   provider_reference=reference,
                   notice=error or "Payment prompt sent. No funds recorded until verified."),202

@mobile_api.get("/payments/mobile/<payment_id>")
@jwt_required()
def mobile_payment_status(payment_id):
    user = current_user()
    payment = db.session.get(Payment,payment_id)
    if not payment:
        abort(404)
    visible_invoice(user,db.session.get(Invoice,payment.invoice_id))
    attempt = db.session.query(ProviderAttempt).filter_by(payment_id=payment.id).first()
    if attempt is None:
        abort(404)
    return jsonify(payment=serialize(payment,"id","invoice_id","amount_ugx","status","method"),
                   provider=serialize(attempt,"provider","reference","status","last_verified_at",
                                      "verification_attempts"))

@mobile_api.post("/payments/mobile/<payment_id>/verify")
@jwt_required()
@limiter.limit("4 per minute")
def verify_mobile_payment(payment_id):
    user = current_user()
    payment = db.session.get(Payment,payment_id)
    if not payment:
        abort(404)
    visible_invoice(user,db.session.get(Invoice,payment.invoice_id))
    if payment.method not in PROVIDERS:
        abort(404)
    if os.getenv(payment.method+"_ENABLED","false").lower() != "true":
        return fail("Provider verification is not enabled",503)
    try:
        result = verify_and_post(payment.id)
    except (ProviderError,SettlementError):
        return fail("Verification could not be completed. Check again later.",503)
    return jsonify(result=result)
