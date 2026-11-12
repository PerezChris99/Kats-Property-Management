"""Role-bound, database-aggregated workspace analytics.

Each endpoint returns chart-ready series. No client-supplied landlord/tenant ID:
the user and tenant mapping always come from the verified JWT, and PostgreSQL
RLS still applies independently to the SQL session.
"""
from datetime import date
from flask import Blueprint, jsonify
from sqlalchemy import case, distinct, exists, func, select
from .api import roles
from .extensions import db
from .models import Room, Property, Tenant, Lease, Invoice, Payment, MaintenanceRequest

workspace_analytics_api = Blueprint("workspace_analytics", __name__)
STAFF = ("OWNER", "MANAGER", "ACCOUNTANT", "SUPER_ADMIN")
OPEN_TICKETS = ("OPEN", "ASSIGNED", "IN_PROGRESS", "ON_HOLD")


def _bucket(column):
    # DATE_TRUNC on PostgreSQL; strftime only for the isolated SQLite test suite.
    if db.engine.dialect.name == "postgresql":
        return func.date_trunc("month", column)
    return func.strftime("%Y-%m-01", column)


def _month(value):
    return value.strftime("%Y-%m") if hasattr(value, "strftime") else str(value)[:7]


def _tenant_id(user):
    return db.session.query(Tenant.id).filter(Tenant.user_id == user.id).scalar()


@workspace_analytics_api.get("/analytics/landlord/occupancy")
@roles(*STAFF)
def landlord_occupancy(_user):
    grouped = (db.session.query(Room.status, func.count(Room.id))
               .filter(Room.status != "ARCHIVED")
               .group_by(Room.status).order_by(Room.status).all())
    return jsonify(points=[{"name":status.replace("_", " ").title(), "value":int(count)}
                           for status, count in grouped], unit="rooms",
                   method="Current recorded room states; archived rooms excluded.")


@workspace_analytics_api.get("/analytics/landlord/collections-by-property")
@roles(*STAFF)
def landlord_collections_by_property(_user):
    grouped = (db.session.query(Property.id, Property.name,
                                 func.coalesce(func.sum(Payment.amount_ugx), 0))
               .join(Room, Room.property_id == Property.id)
               .join(Lease, Lease.room_id == Room.id)
               .join(Invoice, Invoice.lease_id == Lease.id)
               .join(Payment, Payment.invoice_id == Invoice.id)
               .filter(Payment.status == "RECONCILED", Payment.reversed_at.is_(None))
               .group_by(Property.id, Property.name)
               .order_by(Property.name).all())
    return jsonify(points=[{"name":name, "value":int(total)}
                           for _id, name, total in grouped],
                   unit="UGX", method="Independently reconciled, unreversed payments allocated to each property's invoices.")


@workspace_analytics_api.get("/analytics/landlord/monthly")
@roles(*STAFF)
def landlord_monthly(_user):
    paid_month = _bucket(Payment.settled_at)
    billed_month = _bucket(Invoice.period_start)
    collections = (db.session.query(paid_month, func.sum(Payment.amount_ugx))
                   .filter(Payment.status == "RECONCILED",
                           Payment.reversed_at.is_(None), Payment.settled_at.isnot(None))
                   .group_by(paid_month).all())
    billed = (db.session.query(billed_month,
                               func.sum(Invoice.total_ugx - Invoice.credit_ugx))
              .filter(Invoice.status != "VOID")
              .group_by(billed_month).all())
    paid = {_month(month): int(amount) for month, amount in collections}
    invoices = {_month(month): int(amount) for month, amount in billed}
    months = sorted(set(paid) | set(invoices))[-12:]
    return jsonify(points=[{"name":month, "value":paid.get(month, 0),
                            "secondary":invoices.get(month, 0)} for month in months],
                   unit="UGX",
                   method=("Reconciled unreversed payments grouped by actual settlement month. "
                           "Invoices grouped by rent period; these are different accounting events."))


@workspace_analytics_api.get("/analytics/landlord/tenant-overlap")
@roles(*STAFF)
def landlord_tenant_overlap(_user):
    # Each set contains distinct tenants with at least one active lease.
    active = exists(select(Lease.id).where(Lease.tenant_id == Tenant.id,
                                           Lease.status == "ACTIVE")).correlate(Tenant)
    overdue = exists(select(Invoice.id).where(
        Invoice.tenant_id == Tenant.id, Invoice.status != "VOID",
        Invoice.due_date < date.today(),
        Invoice.total_ugx > Invoice.paid_ugx + Invoice.credit_ugx)).correlate(Tenant)
    has_ticket = exists(select(MaintenanceRequest.id).where(
        MaintenanceRequest.tenant_id == Tenant.id,
        MaintenanceRequest.status.in_(OPEN_TICKETS))).correlate(Tenant)
    current = ~overdue
    def count_when(condition):
        return func.count(distinct(case((condition, Tenant.id), else_=None)))
    row = db.session.query(
        count_when(active & current),
        count_when(active & has_ticket),
        count_when(active & current & has_ticket),
        count_when(active),
    ).one()
    return jsonify(current=int(row[0]), maintenance=int(row[1]),
                   both=int(row[2]), total=int(row[3]),
                   method=("Active-lease tenants current on rent (no unpaid invoice past its due date) "
                           "intersected with tenants having an OPEN/ASSIGNED/IN_PROGRESS/ON_HOLD maintenance ticket."))


@workspace_analytics_api.get("/analytics/landlord/property-scores")
@roles(*STAFF)
def landlord_property_scores(_user):
    # Independent SQL GROUP BY queries avoid multiplicative joins across rooms,
    # invoices and maintenance requests.
    room_counts = (db.session.query(Room.property_id, func.count(Room.id),
                    func.sum(case((Room.status == "OCCUPIED", 1), else_=0)))
                   .filter(Room.status != "ARCHIVED").group_by(Room.property_id).all())
    finance = (db.session.query(Room.property_id,
                   func.coalesce(func.sum(Invoice.paid_ugx), 0),
                   func.coalesce(func.sum(Invoice.total_ugx - Invoice.credit_ugx), 0))
               .join(Lease, Lease.room_id == Room.id)
               .join(Invoice, Invoice.lease_id == Lease.id)
               .filter(Invoice.status != "VOID").group_by(Room.property_id).all())
    tickets = (db.session.query(Room.property_id, func.count(MaintenanceRequest.id),
                 func.sum(case((MaintenanceRequest.status.in_(OPEN_TICKETS), 1), else_=0)))
               .join(MaintenanceRequest, MaintenanceRequest.room_id == Room.id)
               .group_by(Room.property_id).all())
    rooms = {pid:(int(total),int(occupied or 0)) for pid,total,occupied in room_counts}
    rents = {pid:(int(paid),int(total)) for pid,paid,total in finance}
    jobs = {pid:(int(total),int(open_count or 0)) for pid,total,open_count in tickets}
    points = []
    for pid, name in db.session.query(Property.id, Property.name).order_by(Property.name).all():
        total,occupied = rooms.get(pid,(0,0))
        applied,billed = rents.get(pid,(0,0))
        ticket_total,open_count = jobs.get(pid,(0,0))
        points.append({"name":name,
                       "occupancy":round(100*occupied/total) if total else 0,
                       "collection":round(100*applied/billed) if billed else 0,
                       "maintenance":round(100*(ticket_total-open_count)/ticket_total) if ticket_total else 0,
                       "units":total, "tickets":ticket_total})
    return jsonify(points=points, unit="percent",
                   method=("Occupancy: occupied / non-archived units. Collection: applied net rent / "
                           "net invoiced rent. Maintenance: closed or otherwise non-open tickets / all tickets. "
                           "A metric with no observations is shown as 0, not inferred performance."))


@workspace_analytics_api.get("/analytics/tenant/payment-status")
@roles("TENANT")
def tenant_payment_status(user):
    tenant_id = _tenant_id(user)
    if not tenant_id:
        return jsonify(points=[], unit="invoices")
    remaining = Invoice.total_ugx - Invoice.paid_ugx - Invoice.credit_ugx
    label = case((remaining <= 0, "Paid"),
                 (Invoice.due_date < date.today(), "Overdue"), else_="Due")
    grouped = (db.session.query(label, func.count(Invoice.id))
               .filter(Invoice.tenant_id == tenant_id, Invoice.status != "VOID")
               .group_by(label).order_by(label).all())
    return jsonify(points=[{"name":status, "value":int(count)} for status,count in grouped],
                   unit="invoices",
                   method="Paid: no remaining invoice balance. Overdue: balance remains past due. Due: balance remains but due date not passed.")


@workspace_analytics_api.get("/analytics/tenant/applied-payments")
@roles("TENANT")
def tenant_applied_payments(user):
    tenant_id = _tenant_id(user)
    if not tenant_id:
        return jsonify(points=[], unit="UGX")
    month = _bucket(Invoice.period_start)
    rows = (db.session.query(month, func.sum(Invoice.paid_ugx))
            .filter(Invoice.tenant_id == tenant_id, Invoice.status != "VOID")
            .group_by(month).order_by(month).all())
    return jsonify(points=[{"name":_month(month), "value":int(value)} for month,value in rows],
                   unit="UGX",
                   method="Payments applied to invoices by billed rent period, not necessarily the cash settlement date.")


@workspace_analytics_api.get("/analytics/tenant/balance-trend")
@roles("TENANT")
def tenant_balance_trend(user):
    tenant_id = _tenant_id(user)
    if not tenant_id:
        return jsonify(points=[], unit="UGX")
    month = _bucket(Invoice.period_start)
    amounts = (db.session.query(
        month.label("month"),
        func.sum(Invoice.total_ugx - Invoice.paid_ugx - Invoice.credit_ugx).label("balance"))
        .filter(Invoice.tenant_id == tenant_id, Invoice.status != "VOID")
        .group_by(month).subquery())
    rows = (db.session.query(amounts.c.month,
                     func.sum(amounts.c.balance).over(order_by=amounts.c.month))
            .order_by(amounts.c.month).all())
    return jsonify(points=[{"name":_month(month), "value":int(value)} for month,value in rows],
                   unit="UGX",
                   method="Cumulative outstanding balance from net rent invoices by billing period, calculated with a SQL window function.")


@workspace_analytics_api.get("/analytics/landlord/portfolio")
@roles(*STAFF)
def landlord_portfolio(_user):
    """Single-owner unit counts by property, grouped in SQL."""
    grouped = (db.session.query(
        Property.id, Property.name, Property.district,
        func.count(Room.id),
        func.coalesce(func.sum(case((Room.status == "OCCUPIED", 1), else_=0)), 0),
        func.coalesce(func.sum(case((Room.status == "VACANT", 1), else_=0)), 0),
    ).outerjoin(Room, (Room.property_id == Property.id) &
                (Room.status != "ARCHIVED"))
        .group_by(Property.id, Property.name, Property.district)
        .order_by(Property.name, Property.id).all())
    points = [{"id": pid, "name": name, "district": district,
               "value": int(total), "occupied": int(occupied),
               "vacant": int(vacant)}
              for pid, name, district, total, occupied, vacant in grouped]
    return jsonify(points=points, unit="rooms",
                   method=("One owner's non-archived units grouped by property. "
                           "Occupied and vacant are recorded room states; "
                           "other room states are included in total units."))


@workspace_analytics_api.get("/analytics/tenant/payment-history")
@roles("TENANT")
def tenant_payment_history(user):
    """Actual verified settlement months, not rent invoice billing months."""
    tenant_id = _tenant_id(user)
    if not tenant_id:
        return jsonify(points=[], unit="UGX")
    month = _bucket(Payment.settled_at)
    rows = (db.session.query(month, func.sum(Payment.amount_ugx))
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .filter(Invoice.tenant_id == tenant_id,
                    Payment.status == "RECONCILED",
                    Payment.reversed_at.is_(None),
                    Payment.settled_at.isnot(None))
            .group_by(month).order_by(month).all())
    return jsonify(points=[{"name": _month(period), "value": int(value)}
                           for period, value in rows], unit="UGX",
                   method=("Verified unreversed receipts by actual settlement month. "
                           "Legacy payments without a verified settlement date are excluded."))
