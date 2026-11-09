"""Verified collection trends and approved expenses, not invented cashflows."""
from datetime import date, datetime, timezone
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from .api import roles, fail
from .extensions import db
from .models import Invoice, Payment, Expense

analytics_api=Blueprint("analytics",__name__)
MONTH_NAMES=("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec")

def year_param(value):
    try:
        year=int(value) if value else datetime.now(timezone.utc).year
    except (TypeError,ValueError):
        raise ValueError("Year must be YYYY")
    if not 2000<=year<=2099:
        raise ValueError("Year must be between 2000 and 2099")
    return year

@analytics_api.get("/reports/annual-trends")
@roles("OWNER","MANAGER","ACCOUNTANT","SUPER_ADMIN")
def annual_trends(user):
    try:
        year=year_param(request.args.get("year"))
    except ValueError as exc:
        return fail(str(exc),400)
    start=date(year,1,1)
    end=date(year+1,1,1)
    start_datetime=datetime(year,1,1,tzinfo=timezone.utc)
    end_datetime=datetime(year+1,1,1,tzinfo=timezone.utc)

    pmonth=func.extract("month",Payment.settled_at)
    collections=db.session.query(pmonth,func.sum(Payment.amount_ugx)).filter(
        Payment.status=="RECONCILED",
        Payment.settled_at>=start_datetime,
        Payment.settled_at<end_datetime).group_by(pmonth).all()

    imonth=func.extract("month",Invoice.period_start)
    invoiced=db.session.query(imonth,func.sum(Invoice.total_ugx-Invoice.credit_ugx)).filter(
        Invoice.status!="VOID",Invoice.period_start>=start,
        Invoice.period_start<end).group_by(imonth).all()

    emonth=func.extract("month",Expense.incurred_on)
    expense=db.session.query(emonth,func.sum(Expense.amount_ugx)).filter(
        Expense.status=="APPROVED",Expense.incurred_on>=start,
        Expense.incurred_on<end).group_by(emonth).all()
    payments={int(month):int(amount) for month,amount in collections}
    bills={int(month):int(amount) for month,amount in invoiced}
    costs={int(month):int(amount) for month,amount in expense}
    points=[]
    for index,short in enumerate(MONTH_NAMES,1):
        points.append({
            "month":f"{year}-{index:02d}",
            "label":short,
            "verified_collections_ugx":payments.get(index,0),
            "net_invoiced_ugx":bills.get(index,0),
            "approved_expenses_incurred_ugx":costs.get(index,0),
        })
    legacy=db.session.query(func.coalesce(func.sum(Payment.amount_ugx),0)).filter(
        Payment.status=="RECONCILED",Payment.settled_at.is_(None)).scalar() or 0
    return jsonify(
        year=year,points=points,
        totals={"verified_collections_ugx":sum(payments.values()),
                "net_invoiced_ugx":sum(bills.values()),
                "approved_expenses_incurred_ugx":sum(costs.values())},
        legacy_verified_without_settlement_date_ugx=int(legacy),
        methodology=("Collections are payments independently reconciled and not reversed, "
                     "grouped by their verified settlement timestamp. Historical reconciled "
                     "payments with no reliable timestamp are disclosed separately and "
                     "excluded from the monthly chart. Expenses are grouped by incurred "
                     "date after independent approval, NOT by bank cash-disbursement date. "
                     "This chart is not a cashflow statement or audited profit-and-loss account.")
    )
