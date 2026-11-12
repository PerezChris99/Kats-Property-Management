"""Single-owner arrears control based on unpaid issued invoices.

Records are grouped by the invoice due date, using the Uganda business date.
This endpoint does not equate invoices to verified bank receivables.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, jsonify, request, abort
from sqlalchemy import case, func
from .api import roles
from .extensions import db
from .models import Invoice, Tenant

arrears_api = Blueprint("arrears_api", __name__)
ARREARS_STATES = ("ISSUED", "OVERDUE", "PARTIALLY_PAID")

def aging_query(today):
    outstanding = Invoice.total_ugx - Invoice.paid_ugx - Invoice.credit_ugx
    days = (today - Invoice.due_date)
    # PostgreSQL and SQLite use different date-arithmetic semantics; classify
    # by cutoff dates instead of subtracting SQL date expressions.
    from datetime import timedelta
    aging = case(
        (Invoice.due_date >= today - timedelta(days=30), "1–30 days"),
        (Invoice.due_date >= today - timedelta(days=60), "31–60 days"),
        (Invoice.due_date >= today - timedelta(days=90), "61–90 days"),
        else_="90+ days",
    )
    query = db.session.query(Invoice).filter(
        Invoice.status.in_(ARREARS_STATES),
        Invoice.due_date < today,
        outstanding > 0,
    )
    return query, aging, outstanding


@arrears_api.get("/finance/arrears-aging")
@roles("OWNER", "ACCOUNTANT", "MANAGER", "SUPER_ADMIN")
def arrears_aging(_user):
    today = datetime.now(ZoneInfo("Africa/Kampala")).date()
    query, bucket, outstanding = aging_query(today)
    totals = (db.session.query(
        bucket.label("bucket"), func.count(Invoice.id),
        func.coalesce(func.sum(outstanding), 0))
        .filter(Invoice.status.in_(ARREARS_STATES), Invoice.due_date < today,
                outstanding > 0)
        .group_by(bucket).all())
    buckets = {name: {"name": name, "invoices": 0, "value": 0}
               for name in ("1–30 days", "31–60 days", "61–90 days", "90+ days")}
    for name, count, value in totals:
        buckets[name] = {"name": name, "invoices": int(count), "value": int(value)}
    return jsonify(points=list(buckets.values()), unit="UGX",
                   as_of=today.isoformat(), overdue_invoices=sum(x["invoices"] for x in buckets.values()),
                   outstanding_ugx=sum(x["value"] for x in buckets.values()),
                   note="Unpaid issued/overdue/partially-paid invoices only; balances are not proof of settled cash.")


@arrears_api.get("/finance/arrears-invoices")
@roles("OWNER", "ACCOUNTANT", "MANAGER", "SUPER_ADMIN")
def arrears_invoices(_user):
    try:
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("page_size", "25"))
    except (ValueError, TypeError):
        abort(400, description="Invalid pagination")
    if not 1 <= page <= 200 or not 1 <= page_size <= 100:
        abort(400, description="Invalid pagination")
    today = datetime.now(ZoneInfo("Africa/Kampala")).date()
    query, _bucket, outstanding = aging_query(today)
    total = query.count()
    rows = (query.join(Tenant, Invoice.tenant_id == Tenant.id)
            .with_entities(Invoice.id, Invoice.invoice_number, Invoice.due_date,
                           Invoice.status, Tenant.full_name, outstanding.label("due_ugx"))
            .order_by(Invoice.due_date, Invoice.id)
            .offset((page-1)*page_size).limit(page_size).all())
    return jsonify(items=[{
        "invoice_id": row.id, "invoice_number": row.invoice_number,
        "due_date": row.due_date.isoformat(), "status": row.status,
        "tenant_name": row.full_name, "outstanding_ugx": int(row.due_ugx)
    } for row in rows], total=total, page=page, page_size=page_size,
        as_of=today.isoformat())
