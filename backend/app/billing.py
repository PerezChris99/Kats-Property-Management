"""Safe, idempotent monthly rent invoicing.

Only whole months fully covered by an active lease are billed automatically.
Partial lease months require manual review; no guessed proration policy is applied.
"""
import calendar
from datetime import date
from flask import current_app
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import User, Lease, Invoice, LedgerEntry, AuditLog, new_id

SYSTEM_ACTOR_ID = "00000000-0000-4000-8000-000000000001"

def system_actor():
    actor = db.session.get(User, SYSTEM_ACTOR_ID)
    if not actor:
        actor = User(
            id=SYSTEM_ACTOR_ID, full_name="Kats Scheduled Billing",
            email="kats-billing@internal.invalid", role="SERVICE",
            is_active=False, password_hash="login-disabled"
        )
        db.session.add(actor)
        db.session.flush()
    return actor

def generate_monthly_rent(target_month: date, actor: User | None = None):
    """Create each eligible invoice exactly once; reject partial months.

    Call from a worker or a server-authorized staff request. Never call from frontend directly.
    """
    first = target_month.replace(day=1)
    last = date(first.year, first.month, calendar.monthrange(first.year, first.month)[1])
    if actor is None:
        actor = system_actor()

    issued, existing, needs_review = 0, 0, 0
    leases = (
        db.session.query(Lease)
        .filter(Lease.status == "ACTIVE")
        .with_for_update()
        .all()
    )
    for lease in leases:
        # If the lease has no exposure in this month, skip entirely.
        if lease.end_date < first or lease.start_date > last:
            continue
        if lease.start_date > first or lease.end_date < last:
            needs_review += 1
            continue
        duplicate = db.session.query(Invoice.id).filter_by(
            lease_id=lease.id, period_start=first, period_end=last
        ).first()
        if duplicate:
            existing += 1
            continue
        due = date(first.year, first.month, lease.due_day)
        invoice = Invoice(
            invoice_number="KATS-" + new_id()[:12].upper(),
            lease_id=lease.id, tenant_id=lease.tenant_id,
            period_start=first, period_end=last, due_date=due,
            total_ugx=lease.rent_ugx, paid_ugx=0, status="ISSUED"
        )
        db.session.add(invoice)
        db.session.flush()
        db.session.add(LedgerEntry(invoice_id=invoice.id, event="INVOICE_ISSUED", amount_ugx=invoice.total_ugx))
        db.session.add(AuditLog(
            actor_id=actor.id, action="billing.monthly_invoice_issued",
            target_type="invoice", target_id=invoice.id,
            details={"lease_id": lease.id, "period": first.isoformat()}
        ))
        issued += 1
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # Concurrent workers can race on uniqueness; do not report false success.
        current_app.logger.warning("Monthly billing encountered a uniqueness conflict")
        raise
    return {"month": first.isoformat(), "issued": issued,
            "already_exists": existing, "requires_manual_proration_review": needs_review}
