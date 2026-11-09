"""Contract-controlled prorated rent preview and explicit two-person-approved billing.

Policy is never assumed by the scheduler; a finance officer must explicitly
confirm ACTUAL_CALENDAR_DAYS for partial-month or rent-change billing.
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from flask import Blueprint, abort, jsonify, request
from sqlalchemy.exc import IntegrityError
from .api import roles, data, required_string, parse_date, fail, serialize, audit
from .extensions import db
from .models import Invoice, InvoiceLine, LedgerEntry, Lease, LeaseAmendment, new_id

proration_api=Blueprint("proration",__name__)
STAFF=("OWNER","MANAGER","ACCOUNTANT","SUPER_ADMIN")
ISSUERS=("OWNER","ACCOUNTANT","SUPER_ADMIN")
POLICY="ACTUAL_CALENDAR_DAYS"

def calculation(lease,month):
    first=month.replace(day=1)
    last=date(first.year,first.month,calendar.monthrange(first.year,first.month)[1])
    start=max(first,lease.start_date)
    end=min(last,lease.end_date)
    if start>end:
        raise ValueError("Lease does not cover the requested month")
    changes=db.session.query(LeaseAmendment).filter(
        LeaseAmendment.lease_id==lease.id,LeaseAmendment.effective_date<=end
    ).order_by(LeaseAmendment.effective_date).all()
    runs=[]
    previous=None
    day=start
    while day<=end:
        applicable=next((x.new_rent_ugx for x in reversed(changes)
                         if x.effective_date<=day),lease.rent_ugx)
        if runs and runs[-1]["monthly_rent_ugx"]==applicable:
            runs[-1]["to"]=day
            runs[-1]["days"]+=1
        else:
            runs.append({"from":day,"to":day,"monthly_rent_ugx":applicable,"days":1})
        day+=timedelta(days=1)
    days_in_month=(last-first).days+1
    total=0
    for segment in runs:
        fraction=Decimal(segment["monthly_rent_ugx"])*Decimal(segment["days"])/Decimal(days_in_month)
        segment["amount_ugx"]=int(fraction.quantize(Decimal("1"),rounding=ROUND_HALF_UP))
        segment["from"]=segment["from"].isoformat()
        segment["to"]=segment["to"].isoformat()
        total+=segment["amount_ugx"]
    return {"period_start":start,"period_end":end,"month":first.isoformat(),
            "policy":POLICY,"days_in_month":days_in_month,"segments":runs,
            "amount_ugx":total,"contract_review_required":True}

def parse_month(value):
    if not isinstance(value,str) or len(value)!=7 or value[4]!="-":
        raise ValueError("Month must be YYYY-MM")
    try:
        month=date.fromisoformat(value+"-01")
    except ValueError as exc:
        raise ValueError("Invalid month") from exc
    return month

@proration_api.get("/billing/proration/preview")
@roles(*STAFF)
def preview_prorated_rent(user):
    try:
        month=parse_month(request.args.get("month"))
    except ValueError as exc:
        return fail(str(exc))
    lease_id=request.args.get("lease_id","")
    lease=db.session.get(Lease,lease_id)
    if not lease or lease.status!="ACTIVE":
        return fail("Active lease required",404)
    try:
        result=calculation(lease,month)
    except ValueError as exc:
        return fail(str(exc),409)
    result["period_start"]=result["period_start"].isoformat()
    result["period_end"]=result["period_end"].isoformat()
    return jsonify(preview=result)

@proration_api.post("/billing/proration/issue")
@roles(*ISSUERS)
def issue_prorated_rent(user):
    obj=data()
    try:
        month=parse_month(obj.get("month"))
    except ValueError as exc:
        return fail(str(exc))
    if obj.get("policy")!=POLICY or obj.get("confirm_policy") is not True:
        return fail("Approved contract proration policy must be explicitly confirmed")
    lease_id=required_string(obj,"lease_id")
    reason=required_string(obj,"reason",500)
    lease=db.session.query(Lease).filter_by(id=lease_id).with_for_update().first()
    if not lease or lease.status!="ACTIVE":
        return fail("Active lease required",404)
    try:
        result=calculation(lease,month)
    except ValueError as exc:
        return fail(str(exc),409)
    if result["amount_ugx"]<=0:
        return fail("Prorated rent must be positive",409)
    start,end=result["period_start"],result["period_end"]
    overlap=db.session.query(Invoice.id).join(InvoiceLine,InvoiceLine.invoice_id==Invoice.id).filter(
        Invoice.lease_id==lease.id,Invoice.period_start<=end,
        Invoice.period_end>=start,Invoice.status!="VOID",
        InvoiceLine.charge_type=="RENT"
    ).first()
    if overlap:
        return fail("Rent is already invoiced for an overlapping lease period",409)
    due=parse_date(obj.get("due_date"))
    if due<start or due>end+timedelta(days=60):
        return fail("Due date must be within billing period or 60 days after it",400)
    invoice=Invoice(
        invoice_number="KATS-"+new_id()[:12].upper(),
        lease_id=lease.id,tenant_id=lease.tenant_id,period_start=start,period_end=end,
        due_date=due,total_ugx=result["amount_ugx"],status="ISSUED"
    )
    db.session.add(invoice)
    try:
        db.session.flush()
        for segment in result["segments"]:
            line=InvoiceLine(
                invoice_id=invoice.id,charge_type="RENT",
                description="Prorated rent "+segment["from"]+" to "+segment["to"]+
                    " ("+str(segment["days"])+"/"+str(result["days_in_month"])+
                    " days at "+str(segment["monthly_rent_ugx"])+" UGX/month)",
                quantity=1,unit_price_ugx=segment["amount_ugx"],
                amount_ugx=segment["amount_ugx"])
            db.session.add(line)
        db.session.add(LedgerEntry(invoice_id=invoice.id,event="INVOICE_ISSUED",
                                   amount_ugx=invoice.total_ugx))
        audit(user,"billing.proration_issued","invoice",invoice.id,
              policy=POLICY,reason=reason,month=result["month"],
              calculated_amount_ugx=result["amount_ugx"])
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Overlapping or duplicate billing command",409)
    return jsonify(invoice=serialize(invoice,"id","invoice_number","period_start",
                                    "period_end","total_ugx","status"),
                   policy=POLICY,reason=reason),201
