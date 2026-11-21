"""Receive rent in advance, hold it as a liability, then apply it to lease invoices."""
from datetime import datetime, timezone
from flask import Blueprint, abort, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .api import audit, data, fail, required_string, roles, serialize, ugx
from .extensions import db
from .finance.ledger import GLPostingError, post_event, reverse_posted, today
from .models import Lease, Room, Tenant, Invoice, Payment, LedgerEntry, RentAdvance
from .journal import post_receipt_journal

advances = Blueprint("rent_advances", __name__)
STAFF = ("OWNER", "ACCOUNTANT", "MANAGER", "SUPER_ADMIN")


@advances.errorhandler(GLPostingError)
def posting_error(error):
    db.session.rollback()
    return fail(str(error), 409)


def locked(identity):
    return db.first_or_404(db.select(RentAdvance).where(RentAdvance.id == identity).with_for_update())


def available(row):
    applied = db.session.query(func.sum(Payment.amount_ugx)).filter_by(
        advance_id=row.id, status="RECONCILED").scalar() or 0
    return row.amount_ugx - int(applied) if row.status == "APPROVED" else 0


def details(row):
    result = serialize(row, "id", "lease_id", "amount_ugx", "method", "reference", "status",
                       "created_by", "created_at", "approved_at")
    lease = db.session.get(Lease, row.lease_id)
    result["tenant"] = db.session.get(Tenant, lease.tenant_id).full_name
    result["available_ugx"] = available(row)
    return result


@advances.get("/rent-advances")
@roles(*STAFF, "TENANT")
def listing(user):
    query = db.session.query(RentAdvance).join(Lease).join(Tenant, Lease.tenant_id == Tenant.id)
    if user.role == "TENANT":
        query = query.filter(Tenant.user_id == user.id)
    page = request.args.get("page", 1, type=int)
    if page < 1:
        return fail("Invalid page")
    rows = query.order_by(RentAdvance.created_at.desc(), RentAdvance.id).paginate(
        page=page, per_page=25, error_out=False)
    return jsonify(items=[details(row) for row in rows.items], pages=rows.pages)


@advances.get("/rent-advances/options")
@roles(*STAFF)
def options(_user):
    lease_id = request.args.get("lease_id")
    if lease_id:
        rows = db.session.query(Invoice).filter(Invoice.lease_id == lease_id,
            Invoice.status.notin_(("VOID", "CREDITED", "PAID"))).order_by(Invoice.due_date, Invoice.id).limit(100).all()
        return jsonify(items=[{"id": row.id, "label": row.invoice_number,
            "balance": row.total_ugx - row.credit_ugx - row.paid_ugx} for row in rows])
    search = request.args.get("q", "").strip()[:100]
    query = db.session.query(Lease.id, Tenant.full_name, Room.number).join(
        Tenant, Lease.tenant_id == Tenant.id).join(Room, Lease.room_id == Room.id)
    if search:
        query = query.filter(Tenant.full_name.icontains(search, autoescape=True))
    rows = query.order_by(Tenant.full_name, Lease.start_date.desc(), Lease.id).limit(100).all()
    return jsonify(items=[{"id": row.id, "label": f"{row.full_name} · unit {row.number}"} for row in rows])


@advances.get("/rent-advances/<identity>/receipt.pdf")
@roles(*STAFF, "TENANT")
def receipt_pdf(user, identity):
    from .report_exports import file_response, money, pdf_document, scoped_tenant
    row = db.get_or_404(RentAdvance, identity)
    lease = db.get_or_404(Lease, row.lease_id)
    tenant = scoped_tenant(user, lease.tenant_id)
    room = db.get_or_404(Room, lease.room_id)
    from .models import Property
    property_ = db.get_or_404(Property, room.property_id)
    lines = [f"Tenant: {tenant.full_name}", f"Premises: {property_.name}, unit {room.number}",
             f"Receipt: {row.id}", f"Recorded: {row.created_at.date().isoformat()}",
             f"Amount: {money(row.amount_ugx)}", f"Method: {row.method}",
             f"Reference: {row.reference}", f"Status: {row.status}",
             f"Available to apply: {money(available(row))}"]
    pdf = pdf_document("Kats Properties · Advance rent acknowledgement", lines,
                       footer="Internal receipt. Pending receipts await independent review. Reversed receipts are invalid.")
    return file_response(pdf, "application/pdf", "kats-advance-rent.pdf")


@advances.post("/rent-advances")
@roles(*STAFF)
def record(user):
    obj = data()
    lease = db.get_or_404(Lease, required_string(obj, "lease_id"))
    amount = ugx(obj.get("amount_ugx"), positive=True)
    method = required_string(obj, "method", 25)
    if method not in ("CASH", "BANK_TRANSFER"):
        return fail("Select cash or bank transfer")
    reference = required_string(obj, "reference", 160)
    key = required_string(obj, "idempotency_key", 128)
    def replay():
        existing = db.session.query(RentAdvance).filter_by(idempotency_key=key).first()
        if existing and (existing.lease_id, existing.amount_ugx, existing.method,
                         existing.reference, existing.created_by) == (lease.id, amount, method, reference, user.id):
            return jsonify(details(existing)), 200
        return fail("Advance reference or command already used", 409)
    if db.session.query(RentAdvance.id).filter_by(idempotency_key=key).first():
        return replay()
    if method == "BANK_TRANSFER":
        from .finance.ledger import period_lock
        period_lock("receipt-reference")
        if db.session.query(Payment.id).filter_by(reference=reference).first():
            return fail("Bank reference already recorded as a payment", 409)
    row = RentAdvance(lease_id=lease.id, amount_ugx=amount, method=method, reference=reference,
                      idempotency_key=key, created_by=user.id, status="PENDING")
    db.session.add(row)
    try:
        db.session.flush()
        audit(user, "advance.record", "rent_advance", row.id, amount_ugx=amount)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return replay()
    return jsonify(details(row)), 201


@advances.post("/rent-advances/<identity>/approve")
@roles(*STAFF)
def approve(user, identity):
    row = locked(identity)
    if row.status == "APPROVED":
        return jsonify(details(row))
    if row.status != "PENDING" or row.created_by == user.id:
        return fail("Pending advance requires a different reviewer", 409)
    row.approved_at = datetime.now(timezone.utc)
    row.status = "APPROVED"
    row.reviewed_by = user.id
    lease = db.session.get(Lease, row.lease_id)
    post_event("advance:" + row.id, "RENT_ADVANCE", today(),
               [("CASH_CLEARING", row.amount_ugx, 0), ("TENANT_ADVANCES", 0, row.amount_ugx)],
               actor_id=user.id, property_id=db.session.get(Room, lease.room_id).property_id)
    audit(user, "advance.approve", "rent_advance", row.id)
    db.session.commit()
    return jsonify(details(row))


@advances.post("/rent-advances/<identity>/apply")
@roles(*STAFF)
def apply_credit(user, identity):
    obj = data()
    row = locked(identity)
    invoice_id = required_string(obj, "invoice_id")
    amount = ugx(obj.get("amount_ugx"), positive=True)
    key = required_string(obj, "idempotency_key", 128)
    existing = db.session.query(Payment).filter_by(idempotency_key=key).first()
    if existing:
        if (existing.advance_id, existing.invoice_id, existing.amount_ugx, existing.created_by) != (
                row.id, invoice_id, amount, user.id):
            return fail("Allocation command already used", 409)
        return jsonify(payment_id=existing.id, status=existing.status, advance=details(row))
    invoice = db.session.query(Invoice).filter_by(id=invoice_id, lease_id=row.lease_id).with_for_update().first()
    if invoice is None:
        abort(404)
    if (row.status != "APPROVED" or amount > available(row) or invoice.status == "VOID" or
            amount > invoice.total_ugx - invoice.credit_ugx - invoice.paid_ugx):
        return fail("Allocation exceeds available advance or open invoice balance", 409)
    payment = Payment(advance_id=row.id, invoice_id=invoice.id, amount_ugx=amount,
                      method="ADVANCE_CREDIT", status="RECONCILED", idempotency_key=key,
                      created_by=user.id, reviewed_by=row.reviewed_by, settled_at=row.approved_at)
    db.session.add(payment)
    db.session.flush()
    invoice.paid_ugx += amount
    invoice.status = "PAID" if invoice.paid_ugx + invoice.credit_ugx == invoice.total_ugx else "PARTIALLY_PAID"
    db.session.add(LedgerEntry(invoice_id=invoice.id, payment_id=payment.id,
                               event="PAYMENT_RECEIVED", amount_ugx=amount))
    post_receipt_journal(payment)
    from .finance.ledger import invoice_property
    post_event("payment:" + payment.id, "ADVANCE_ALLOCATION", today(),
               [("TENANT_ADVANCES", amount, 0), ("RENT_RECEIVABLE", 0, amount)],
               actor_id=user.id, property_id=invoice_property(invoice))
    audit(user, "advance.apply", "rent_advance", row.id, payment_id=payment.id, invoice_id=invoice.id)
    db.session.commit()
    return jsonify(payment_id=payment.id, status=payment.status, advance=details(row)), 201


@advances.post("/rent-advances/<identity>/reverse")
@roles("OWNER", "ACCOUNTANT", "SUPER_ADMIN")
def reverse(user, identity):
    reason = required_string(data(), "reason", 500)
    row = locked(identity)
    if row.status == "REVERSED":
        return jsonify(details(row))
    if row.status == "APPROVED":
        if available(row) != row.amount_ugx:
            return fail("Reverse applied invoice payments before correcting this receipt", 409)
        reverse_posted("advance:" + row.id, "advance-reversal:" + row.id, "ADVANCE_REVERSAL", actor_id=user.id)
    row.status = "REVERSED"
    audit(user, "advance.reverse", "rent_advance", row.id, reason=reason)
    db.session.commit()
    return jsonify(details(row))
