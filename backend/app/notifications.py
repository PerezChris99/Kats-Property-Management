"""Idempotent in-app rent and lease notifications.

SMS and email delivery remain separately configurable and must never falsely
report delivery based on local queue creation.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.exc import IntegrityError
from .extensions import db
from .models import Invoice, Lease, Tenant, User
from .extra_models import Notification

KAMPALA = ZoneInfo("Africa/Kampala")
REMINDER_AGE_DAYS = {-7, 0, 1, 7, 14, 30}

def add_notification(user_id, kind, title, body, key, channel="IN_APP"):
    if channel not in ("IN_APP", "EMAIL", "SMS"):
        raise ValueError("Unsupported notification channel")
    record = db.session.query(Notification).filter_by(dedupe_key=key).first()
    if record:
        return record, False
    item = Notification(user_id=user_id, channel=channel, kind=kind,
                        title=title, body=body, dedupe_key=key,
                        status="DELIVERED" if channel == "IN_APP" else "PENDING",
                        delivered_at=datetime.now(KAMPALA) if channel == "IN_APP" else None)
    db.session.add(item)
    return item, True

def rent_reminder_run(today=None):
    today = today or datetime.now(KAMPALA).date()
    checked, created = 0, 0
    invoices = db.session.query(Invoice).filter(
        Invoice.status.in_(["ISSUED", "PARTIALLY_PAID", "OVERDUE"]),
        Invoice.paid_ugx + Invoice.credit_ugx < Invoice.total_ugx,
        Invoice.due_date >= today - timedelta(days=30),
        Invoice.due_date <= today + timedelta(days=7)
    ).all()
    for invoice in invoices:
        days = (today - invoice.due_date).days
        if days not in REMINDER_AGE_DAYS:
            continue
        tenant = db.session.get(Tenant, invoice.tenant_id)
        if not tenant or not tenant.user_id:
            continue
        user = db.session.get(User, tenant.user_id)
        if not user or not user.is_active:
            continue
        checked += 1
        remaining = invoice.total_ugx - invoice.credit_ugx - invoice.paid_ugx
        label = "due soon" if days < 0 else "due today" if days == 0 else "overdue"
        key = f"rent:{invoice.id}:{today.isoformat()}:{days}"
        _, fresh = add_notification(
            user.id, "RENT_REMINDER", "Rent "+label,
            "A balance of UGX "+format(remaining,",")+" is "+label+
            " for invoice "+invoice.invoice_number+". Check your account for details.",
            key)
        created += int(fresh)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # Dedupe uniqueness handles concurrent schedulers. A retry will resolve it.
        raise
    return {"checked":checked, "notified":created, "date":today.isoformat()}

def expiring_lease_run(today=None):
    today = today or datetime.now(KAMPALA).date()
    leases = db.session.query(Lease).filter(Lease.status == "ACTIVE",
        Lease.end_date >= today, Lease.end_date <= today + timedelta(days=30)).all()
    count = 0
    for lease in leases:
        left = (lease.end_date - today).days
        if left not in (30,14,7,1,0):
            continue
        tenant = db.session.get(Tenant, lease.tenant_id)
        if not tenant or not tenant.user_id:
            continue
        user = db.session.get(User, tenant.user_id)
        if not user or not user.is_active:
            continue
        _, added = add_notification(user.id, "LEASE_EXPIRY", "Lease expiring",
            f"Your current lease expires in {left} day(s). Contact your manager to discuss renewal.",
            f"lease:{lease.id}:{today.isoformat()}")
        count += int(added)
    db.session.commit()
    return {"created":count}
