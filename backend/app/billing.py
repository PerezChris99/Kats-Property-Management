"""Safe, idempotent monthly rent invoicing.

Only whole months fully covered by an active lease are billed automatically.
Partial lease months require manual review; no guessed proration policy is applied.
"""
import calendar
from datetime import date
from flask import current_app
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import User, Lease, LeaseAmendment, Invoice, InvoiceLine, LedgerEntry, AuditLog, new_id

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
    # Stable keyset batches cap memory, row locks and transaction duration.
    # Committed earlier batches survive a failure; retries skip existing invoices.
    last_lease_id = ""
    while True:
        leases = (db.session.query(Lease)
            .filter(Lease.status == "ACTIVE", Lease.id > last_lease_id)
            .order_by(Lease.id)
            .limit(100)
            .with_for_update().all())
        if not leases:
            break
        last_lease_id = leases[-1].id
        # Preload the invoice and rent-change state once per bounded batch.
        # A per-lease SELECT for amendments, full-period duplicates and rent
        # overlap was previously 4*N reads for an N-lease monthly run.
        eligible_ids = [
            lease.id for lease in leases
            if lease.start_date <= first and lease.end_date >= last
        ]
        changed_midmonth = set()
        rates = {}
        duplicate_ids = set()
        overlapping_ids = set()
        if eligible_ids:
            amendments = (db.session.query(LeaseAmendment)
                .filter(LeaseAmendment.lease_id.in_(eligible_ids),
                        LeaseAmendment.effective_date <= last)
                .order_by(LeaseAmendment.effective_date.desc()).all())
            for amendment in amendments:
                if amendment.effective_date > first:
                    changed_midmonth.add(amendment.lease_id)
                elif amendment.lease_id not in rates:
                    rates[amendment.lease_id] = amendment.new_rent_ugx
            duplicate_ids = {
                lease_id for (lease_id,) in db.session.query(Invoice.lease_id)
                .filter(Invoice.lease_id.in_(eligible_ids),
                        Invoice.period_start == first,
                        Invoice.period_end == last).all()
            }
            overlapping_ids = {
                lease_id for (lease_id,) in db.session.query(Invoice.lease_id)
                .join(InvoiceLine, InvoiceLine.invoice_id == Invoice.id)
                .filter(Invoice.lease_id.in_(eligible_ids),
                        Invoice.status != "VOID",
                        Invoice.period_start <= last,
                        Invoice.period_end >= first,
                        InvoiceLine.charge_type == "RENT").all()
            }
        for lease in leases:
            # If the lease has no exposure in this month, skip entirely.
            if lease.end_date < first or lease.start_date > last:
                continue
            if lease.start_date > first or lease.end_date < last:
                needs_review += 1
                continue
            # Midmonth amendments always require approved manual proration.
            if lease.id in changed_midmonth:
                needs_review += 1
                continue
            monthly_rent = rates.get(lease.id, lease.rent_ugx)
            if lease.id in duplicate_ids:
                existing += 1
                continue
            # A previously issued partial rent invoice still blocks this run.
            if lease.id in overlapping_ids:
                needs_review += 1
                continue
            due = date(first.year, first.month, lease.due_day)
            invoice = Invoice(
                invoice_number="KATS-" + new_id()[:12].upper(),
                lease_id=lease.id, tenant_id=lease.tenant_id,
                period_start=first, period_end=last, due_date=due,
                total_ugx=monthly_rent, paid_ugx=0, status="ISSUED"
            )
            db.session.add(invoice)
            db.session.flush()
            db.session.add(InvoiceLine(invoice_id=invoice.id, description="Monthly rent",
                                       charge_type="RENT", quantity=1,
                                       unit_price_ugx=invoice.total_ugx, amount_ugx=invoice.total_ugx))
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
            # Retry is safe: already-committed batches contain immutable invoices.
            current_app.logger.warning("Monthly billing batch conflicted; retry safely")
            raise
    return {"month": first.isoformat(), "issued": issued,
            "already_exists": existing, "requires_manual_proration_review": needs_review}
