"""Read-only, account-scoped presentation reporting.

All comparisons use identical, bounded calendar windows. Verified settlements
use their real settlement timestamp; invoice figures use rent periods. No
client-selected tenant identity or completed-data cache is accepted.
"""
import re
from datetime import date, datetime, timezone
from calendar import monthrange

from flask import Blueprint, jsonify, request
from sqlalchemy import func, exists, select

from .api import roles, fail
from .extensions import db
from .models import Expense, Invoice, Lease, Payment, Property, Room, Tenant

presentation_api = Blueprint("presentation_analytics", __name__)
STAFF = ("OWNER", "MANAGER", "ACCOUNTANT", "SUPER_ADMIN")
ALLOWED = STAFF + ("TENANT",)


def month_at(index):
    return date(index // 12, index % 12 + 1, 1)


def month_number(value):
    if not re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", value or ""):
        raise ValueError("end_month must use YYYY-MM between 2000 and 2099")
    year, month = map(int, value.split("-"))
    return year * 12 + month - 1


def period_args(args):
    raw = args.get("months", "6")
    if raw not in ("3", "6", "12"):
        raise ValueError("months must be 3, 6 or 12")
    count = int(raw)
    now = datetime.now(timezone.utc)
    last = month_number(args.get("end_month", now.strftime("%Y-%m")))
    if last - 2 * count + 1 < 2000 * 12:
        raise ValueError("Not enough history for a previous-period comparison")
    first = month_at(last - count + 1)
    end = month_at(last + 1)
    previous = month_at(last - 2 * count + 1)
    return count, last, previous, first, end


def tenant_scope(user):
    if user.role != "TENANT":
        return None
    return db.session.query(Tenant.id).filter(Tenant.user_id == user.id).scalar()


def _grouped_amount(model, timestamp, amount, start, end, extra=(), tenant_id=None,
                    joins=()):
    """GROUP BY year/month in SQL; never load raw payment data to summarize."""
    year = func.extract("year", timestamp)
    month = func.extract("month", timestamp)
    q = db.session.query(year, month, func.coalesce(func.sum(amount), 0)).select_from(model)
    for entity, condition in joins:
        q = q.join(entity, condition)
    if tenant_id is not None:
        q = q.filter(Invoice.tenant_id == tenant_id)
    q = q.filter(timestamp >= start, timestamp < end, *extra).group_by(year, month)
    return {int(y) * 12 + int(m) - 1: int(total or 0) for y, m, total in q.all()}


def _window_totals(series, lower, upper):
    return sum(value for index, value in series.items() if lower <= index < upper)


def _metric(label, series, count, last, unit="UGX"):
    boundary = last - count + 1
    current = _window_totals(series, boundary, last + 1)
    previous = _window_totals(series, boundary - count, boundary)
    return {
        "label": label, "current": current, "previous": previous, "unit": unit,
        "change_percent": round((current - previous) * 100 / previous, 1) if previous else None,
        "direction": "up" if current > previous else "down" if current < previous else "flat",
    }


def period_payload(user, args):
    """Reusable single source of truth for dashboard charts and PDF/XLSX exports."""
    count, last, earliest, first, end = period_args(args)
    tid = tenant_scope(user)
    is_tenant = user.role == "TENANT"
    # A tenant without a linked rental profile must see *empty*, never global totals.
    if is_tenant and tid is None:
        empty = {}
        paid, invoiced, applied, expenses = empty, empty, empty, empty
    else:
        from_dt = datetime(earliest.year, earliest.month, 1, tzinfo=timezone.utc)
        to_dt = datetime(end.year, end.month, 1, tzinfo=timezone.utc)
        paid = _grouped_amount(
            Payment, Payment.settled_at, Payment.amount_ugx, from_dt, to_dt,
            (Payment.status == "RECONCILED", Payment.reversed_at.is_(None)),
            tid, ((Invoice, Payment.invoice_id == Invoice.id),) if is_tenant else ())
        invoiced = _grouped_amount(
            Invoice, Invoice.period_start, Invoice.total_ugx - Invoice.credit_ugx,
            earliest, end, (Invoice.status != "VOID",), tid)
        applied = _grouped_amount(
            Invoice, Invoice.period_start, Invoice.paid_ugx,
            earliest, end, (Invoice.status != "VOID",), tid) if is_tenant else {}
        expenses = {} if is_tenant else _grouped_amount(
            Expense, Expense.incurred_on, Expense.amount_ugx, earliest, end,
            (Expense.status == "APPROVED",))
    names = {
        "verified_collections": _metric("Verified settlements", paid, count, last),
        "net_invoiced": _metric("Net rent invoiced", invoiced, count, last),
    }
    if is_tenant:
        names["applied_payments"] = _metric("Applied to rent invoices", applied, count, last)
    else:
        names["approved_expenses"] = _metric("Approved incurred expenses", expenses, count, last)
    running_open = 0
    points = []
    for index in range(last - count + 1, last + 1):
        value = invoiced.get(index, 0)
        # Historical invoice periods shown at today's recorded state, not as-of snapshots.
        running_open += value - applied.get(index, 0)
        points.append({
            "name": month_at(index).strftime("%Y-%m"),
            "verified_collections_ugx": paid.get(index, 0),
            "net_invoiced_ugx": value,
            "applied_payments_ugx": applied.get(index, 0) if is_tenant else 0,
            "approved_expenses_ugx": expenses.get(index, 0) if not is_tenant else 0,
            "current_open_invoice_balance_ugx": running_open if is_tenant else 0,
        })
    return {
        "months": count,
        "start_month": first.strftime("%Y-%m"),
        "end_month": month_at(last).strftime("%Y-%m"),
        "previous_start_month": earliest.strftime("%Y-%m"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": names, "points": points,
        "unit": "UGX",
        "method": (
            "Verified unreversed payments use settlement month. Net invoices and applied "
            "payments use invoice period. Approved costs use incurred month. Comparisons "
            "use equal-length consecutive windows; no prior records means no growth %."
            + (" Current invoice balances are grouped by their original billing period; "
               "this is not a reconstructed historical account balance."
               if is_tenant else "")
        ),
    }


@presentation_api.after_request
def private_analytics_cache(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"
    return response


@presentation_api.get("/analytics/period-summary")
@roles(*ALLOWED)
def period_summary(user):
    try:
        return jsonify(period_payload(user, request.args))
    except ValueError as error:
        return fail(str(error), 400)


def _month_bounds(month_text):
    index = month_number(month_text)
    first = month_at(index)
    following = month_at(index + 1)
    return first, following, datetime(first.year, first.month, 1, tzinfo=timezone.utc), (
        datetime(following.year, following.month, 1, tzinfo=timezone.utc))


@presentation_api.get("/analytics/drilldown")
@roles(*ALLOWED)
def analytics_drilldown(user):
    """Exact, limited underlying records; tenant identity derives only from JWT."""
    metric = request.args.get("metric", "")
    month = request.args.get("month", "")
    category = request.args.get("category", "")
    if metric not in ("verified_collections", "net_invoiced", "applied_payments",
                      "approved_expenses", "occupancy", "payment_status", "property_collections",
                      "property_rooms", "overlap"):
        return fail("Unsupported drill-down metric", 400)
    if metric in ("approved_expenses", "occupancy", "property_collections",
                  "property_rooms", "overlap") and user.role == "TENANT":
        return fail("Not authorized", 403)
    if metric in ("applied_payments", "payment_status") and user.role != "TENANT":
        return fail("Not authorized", 403)
    try:
        if metric not in ("occupancy", "payment_status", "property_collections",
                           "property_rooms", "overlap"):
            first, following, from_dt, to_dt = _month_bounds(month)
    except ValueError as error:
        return fail(str(error), 400)
    tenant_id = tenant_scope(user)
    if user.role == "TENANT" and tenant_id is None:
        return jsonify(items=[], total=0, metric=metric, limit=25)
    if metric == "occupancy":
        state = category.upper().replace(" ", "_")
        if state not in ("OCCUPIED", "VACANT", "MAINTENANCE", "RESERVED"):
            return fail("Unsupported occupancy status", 400)
        query = db.session.query(Room).filter(Room.status == state)
        items = [{"title": "Room " + room.number, "subtitle": state,
                  "resource": "rooms", "query": room.number}
                 for room in query.order_by(Room.number, Room.id).limit(25)]
    elif metric == "property_rooms":
        if not category or len(category) > 200:
            return fail("Property name required", 400)
        query = db.session.query(Room, Property).join(
            Property, Property.id == Room.property_id).filter(Property.name == category)
        items = [{"title": f"{prop.name}: room {room.number}",
                  "subtitle": room.status, "resource": "rooms", "query": room.number}
                 for room, prop in query.order_by(Room.number, Room.id).limit(25)]
    elif metric == "property_collections":
        if not category or len(category) > 200:
            return fail("Property name required", 400)
        query = db.session.query(Payment, Invoice).join(
            Invoice, Invoice.id == Payment.invoice_id).join(
            Lease, Lease.id == Invoice.lease_id).join(
            Room, Room.id == Lease.room_id).join(
            Property, Property.id == Room.property_id).filter(
            Property.name == category, Payment.status == "RECONCILED",
            Payment.reversed_at.is_(None))
        items = [{"title": inv.invoice_number,
                  "subtitle": payment.settled_at.date().isoformat() if payment.settled_at
                              else "Legacy verified; undated",
                  "amount_ugx": int(payment.amount_ugx), "resource": "payments",
                  "query": payment.reference or inv.invoice_number}
                 for payment, inv in query.order_by(
                     Payment.created_at.desc(), Payment.id).limit(25)]
    elif metric == "overlap":
        if category not in ("Current rent only", "Both", "Maintenance only", "Neither"):
            return fail("Unsupported intersection", 400)
        active = exists(select(Lease.id).where(
            Lease.tenant_id == Tenant.id, Lease.status == "ACTIVE")).correlate(Tenant)
        overdue = exists(select(Invoice.id).where(
            Invoice.tenant_id == Tenant.id, Invoice.status != "VOID",
            Invoice.due_date < date.today(),
            Invoice.total_ugx > Invoice.paid_ugx + Invoice.credit_ugx)).correlate(Tenant)
        from .models import MaintenanceRequest
        has_ticket = exists(select(MaintenanceRequest.id).where(
            MaintenanceRequest.tenant_id == Tenant.id,
            MaintenanceRequest.status.in_(("OPEN", "ASSIGNED", "IN_PROGRESS", "ON_HOLD"))
        )).correlate(Tenant)
        rent_current = not category in ("Maintenance only", "Neither")
        has_maintenance = category in ("Both", "Maintenance only")
        query = db.session.query(Tenant).filter(active)
        query = query.filter(~overdue if rent_current else overdue)
        query = query.filter(has_ticket if has_maintenance else ~has_ticket)
        items = [{"title": t.full_name, "subtitle": category,
                  "resource": "tenants", "query": t.full_name}
                 for t in query.order_by(Tenant.full_name, Tenant.id).limit(25)]
    elif metric == "payment_status":
        if category not in ("Paid", "Due", "Overdue"):
            return fail("Unsupported invoice status category", 400)
        query = db.session.query(Invoice).filter(
            Invoice.tenant_id == tenant_id, Invoice.status != "VOID")
        outstanding = Invoice.total_ugx - Invoice.credit_ugx - Invoice.paid_ugx
        if category == "Paid":
            query = query.filter(outstanding <= 0)
        elif category == "Overdue":
            query = query.filter(outstanding > 0, Invoice.due_date < date.today())
        else:
            query = query.filter(outstanding > 0, Invoice.due_date >= date.today())
        items = [
            {"title": inv.invoice_number, "subtitle": category,
             "amount_ugx": int(inv.total_ugx - inv.paid_ugx - inv.credit_ugx),
             "resource": "invoices", "query": inv.invoice_number}
            for inv in query.order_by(Invoice.period_start.desc(), Invoice.id).limit(25)]
    elif metric == "approved_expenses":
        query = db.session.query(Expense).filter(
            Expense.status == "APPROVED", Expense.incurred_on >= first,
            Expense.incurred_on < following)
        items = [{"title": row.description[:110], "subtitle": row.incurred_on.isoformat(),
                  "amount_ugx": int(row.amount_ugx), "resource": "expenses",
                  "query": row.description[:80]} for row in
                 query.order_by(Expense.incurred_on.desc(), Expense.id).limit(25)]
    elif metric == "verified_collections":
        query = db.session.query(Payment, Invoice).join(
            Invoice, Invoice.id == Payment.invoice_id).filter(
            Payment.status == "RECONCILED", Payment.reversed_at.is_(None),
            Payment.settled_at >= from_dt, Payment.settled_at < to_dt)
        if tenant_id is not None:
            query = query.filter(Invoice.tenant_id == tenant_id)
        items = [{"title": invoice.invoice_number, "subtitle": row.settled_at.date().isoformat(),
                  "amount_ugx": int(row.amount_ugx), "resource": "payments",
                  "query": row.reference or invoice.invoice_number}
                 for row, invoice in query.order_by(Payment.settled_at.desc(), Payment.id).limit(25)]
    else:
        query = db.session.query(Invoice).filter(
            Invoice.period_start >= first, Invoice.period_start < following,
            Invoice.status != "VOID")
        if tenant_id is not None:
            query = query.filter(Invoice.tenant_id == tenant_id)
        items = [
            {"title": inv.invoice_number, "subtitle": inv.period_start.isoformat(),
             "amount_ugx": int(inv.paid_ugx if metric == "applied_payments"
                               else inv.total_ugx - inv.credit_ugx),
             "resource": "invoices", "query": inv.invoice_number}
            for inv in query.order_by(Invoice.period_start.desc(), Invoice.id).limit(25)]
    return jsonify(items=items, metric=metric, limit=25, truncated=len(items) == 25,
                   generated_at=datetime.now(timezone.utc).isoformat(),
                   note="Read-only record preview; open the source workspace for full details.")
