"""Read-only reconciliation diagnostics; never posts or adjusts balances.

This is an internal control, not proof of settlement against a real bank.
Only verified, unreversed payments count as reconciled cash; invoice
`paid_ugx` is an independently stored applied-balance snapshot.
"""
from flask import Blueprint, jsonify, request, abort
from sqlalchemy import func
from .api import roles
from .extensions import db
from .models import Invoice, Payment

finance_health_api = Blueprint("finance_health", __name__)


@finance_health_api.get("/finance/reconciliation")
@roles("OWNER", "ACCOUNTANT", "SUPER_ADMIN")
def reconciliation_report(_user):
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("page_size", "25"))
    except (TypeError, ValueError):
        abort(400, description="Invalid pagination")
    if page < 1 or page > 200 or per_page < 1 or per_page > 100:
        abort(400, description="Invalid pagination")

    recognized = (db.session.query(
        Payment.invoice_id.label("invoice_id"),
        func.sum(Payment.amount_ugx).label("verified_ugx")
    ).filter(
        Payment.status == "RECONCILED", Payment.reversed_at.is_(None)
    ).group_by(Payment.invoice_id).subquery())

    paid = func.coalesce(recognized.c.verified_ugx, 0)
    anomalies = (db.session.query(
        Invoice.id, Invoice.invoice_number, Invoice.paid_ugx,
        paid.label("verified_ugx"), Invoice.status
    ).outerjoin(recognized, recognized.c.invoice_id == Invoice.id)
        .filter(Invoice.paid_ugx != paid))

    # Show only exceptions, not every tenant's financial information.
    total_exceptions = anomalies.count()
    rows = (anomalies.order_by(Invoice.invoice_number, Invoice.id)
            .offset((page - 1) * per_page).limit(per_page).all())
    return jsonify(
        items=[{
            "invoice_id": row.id,
            "invoice_number": row.invoice_number,
            "applied_ugx": int(row.paid_ugx),
            "verified_ugx": int(row.verified_ugx),
            "difference_ugx": int(row.paid_ugx - row.verified_ugx),
            "invoice_status": row.status
        } for row in rows],
        total_exceptions=total_exceptions,
        page=page,
        page_size=per_page,
        method=("Read-only comparison of non-void and void invoice applied amounts "
                "against RECONCILED unreversed payment records. "
                "This is an internal consistency control, not external bank reconciliation."),
        action=("Investigate discrepancies using payment and invoice histories; "
                "never edit posted balances directly.")
    )
