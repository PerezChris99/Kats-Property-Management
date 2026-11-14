"""Owner/accountant-only GL reports, opening-balance approval and period close.

Never silently import historical entries or allow an operator to approve
their own opening batch. All amounts are integer UGX.
"""
from __future__ import annotations
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
from flask import Blueprint, abort, jsonify, request
from sqlalchemy.exc import IntegrityError
from ..api import roles, data, required_string, audit, fail
from ..extensions import db
from ..models import Property
from .gl_models import GLAccount, GLEvent, GLPeriodClose, GLOpeningBatch
from .ledger import GLPostingError, post_event, validate_lines, close_period, ensure_chart, today
from .reports import trial_balance, balance_sheet, income_statement, detail

gl_api = Blueprint("general_ledger", __name__)
READERS = ("OWNER", "ACCOUNTANT", "SUPER_ADMIN")


def optional_date(name):
    raw = request.args.get(name)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        abort(400, description=name + " must use YYYY-MM-DD")


def optional_property():
    identity = request.args.get("property_id")
    if identity and not db.session.get(Property, identity):
        abort(404)
    return identity or None


def dates():
    start, end = optional_date("from"), optional_date("through")
    if start and end and start > end:
        abort(400, description="from must not exceed through")
    return start, end


@gl_api.get("/finance/gl/accounts")
@roles(*READERS)
def accounts(_user):
    ensure_chart()
    return jsonify(items=[{"code":row.code, "name":row.name, "kind":row.kind, "active":row.active}
                          for row in db.session.query(GLAccount).order_by(GLAccount.code).all()])


@gl_api.get("/finance/gl/trial-balance")
@roles(*READERS)
def get_trial_balance(_user):
    _, end = dates()
    return jsonify(trial_balance(through=end, property_id=optional_property()))


@gl_api.get("/finance/gl/balance-sheet")
@roles(*READERS)
def get_balance_sheet(_user):
    _, end = dates()
    return jsonify(balance_sheet(through=end, property_id=optional_property()))


@gl_api.get("/finance/gl/income-statement")
@roles(*READERS)
def get_income_statement(_user):
    start, end = dates()
    return jsonify(income_statement(from_date=start, through=end,
                                   property_id=optional_property()))


@gl_api.get("/finance/gl/detail")
@roles(*READERS)
def get_detail(_user):
    start, end = dates()
    try:
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("page_size", "25"))
    except (TypeError, ValueError):
        return fail("Invalid GL pagination")
    if not 1 <= page <= 1000 or not 1 <= page_size <= 100:
        return fail("GL pagination outside allowed bounds")
    code = request.args.get("account_code")
    if code and not db.session.get(GLAccount, code):
        return fail("Unknown account")
    return jsonify(detail(account_code=code, from_date=start, through=end,
                          property_id=optional_property(), page=page, page_size=page_size))


def parse_opening_rows(csv_text):
    if not isinstance(csv_text, str) or not 1 <= len(csv_text) <= 60000:
        raise GLPostingError("Opening balance CSV must be bounded text")
    source = io.StringIO(csv_text, newline="")
    try:
        reader = csv.DictReader(source, strict=True)
        if reader.fieldnames != ["account_code", "debit_ugx", "credit_ugx"]:
            raise GLPostingError("Required columns: account_code,debit_ugx,credit_ugx")
        rows = []
        for row in reader:
            if len(rows) >= 200 or None in row or None in row.values():
                raise GLPostingError("Invalid or oversized opening balance CSV")
            code = row["account_code"].strip()
            debit = int(row["debit_ugx"].strip())
            credit = int(row["credit_ugx"].strip())
            rows.append((code, debit, credit))
    except (ValueError, csv.Error, AttributeError) as exc:
        raise GLPostingError("Malformed opening balance CSV") from exc
    return validate_lines(rows)


@gl_api.post("/finance/gl/opening-batches")
@roles(*READERS)
def submit_opening(user):
    obj = data()
    try:
        effective = date.fromisoformat(required_string(obj, "effective_on", 10))
        if effective > today():
            return fail("Opening balances cannot use a future effective date")
        note = required_string(obj, "note", 500)
        rows = parse_opening_rows(obj.get("csv_text"))
    except (ValueError, GLPostingError) as exc:
        return fail(str(exc))
    canonical = json.dumps([effective.isoformat(), rows], separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if db.session.query(GLOpeningBatch.id).filter_by(import_sha256=fingerprint).first():
        return fail("Duplicate opening balance batch; inspect the existing approval queue", 409)
    row = GLOpeningBatch(effective_on=effective, rows=rows, note=note,
                         submitted_by=user.id, import_sha256=fingerprint, status="PENDING")
    db.session.add(row)
    try:
        db.session.flush()
        audit(user, "gl.opening_submitted", "gl_opening_batch", row.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Duplicate opening balance import", 409)
    return jsonify(batch={"id": row.id, "status": row.status,
                          "effective_on": row.effective_on.isoformat()},
                   notice="Pending independent accountant/owner approval; no ledger entry posted."), 201


@gl_api.get("/finance/gl/opening-batches")
@roles(*READERS)
def opening_batches(_user):
    items = db.session.query(GLOpeningBatch).order_by(
        GLOpeningBatch.created_at.desc()).limit(100).all()
    return jsonify(items=[
        {"id":row.id,"status":row.status,
         "effective_on":row.effective_on.isoformat(),"note":row.note,
         "submitted_by":row.submitted_by,"approved_by":row.approved_by,
         "line_count":len(row.rows)}
        for row in items
    ])


@gl_api.post("/finance/gl/opening-batches/<batch_id>/review")
@roles(*READERS)
def approve_opening(user, batch_id):
    obj = data()
    decision = required_string(obj, "decision", 20).upper()
    reason = required_string(obj, "reason", 500)
    if decision not in ("APPROVE", "REJECT"):
        return fail("Decision must be APPROVE or REJECT")
    batch = db.session.query(GLOpeningBatch).filter_by(id=batch_id).with_for_update().first()
    if not batch:
        abort(404)
    if batch.status != "PENDING":
        return fail("Opening batch was already reviewed", 409)
    if batch.submitted_by == user.id:
        return fail("Two-person review is required for opening balances", 403)
    try:
        if decision == "APPROVE":
            post_event("opening:" + batch.id, "OPENING_BALANCES", batch.effective_on,
                       [tuple(item) for item in batch.rows], actor_id=user.id)
        batch.status = "POSTED" if decision == "APPROVE" else "REJECTED"
        batch.approved_by = user.id
        batch.approved_at = datetime.now(timezone.utc)
        audit(user, "gl.opening_review", "gl_opening_batch", batch.id,
              decision=decision, reason=reason)
        db.session.commit()
    except GLPostingError as exc:
        db.session.rollback()
        return fail(str(exc), 409)
    return jsonify(batch={"id":batch.id,"status":batch.status},
                   notice="Approved balanced entry appended; no historical invoice rows changed.")


@gl_api.post("/finance/gl/periods/<period>/close")
@roles(*READERS)
def close_period_api(user, period):
    reason = required_string(data(), "reason", 500)
    # Incomplete historical opening records make reported balances unreliable.
    # Conservatively block ALL closes until their independent review.
    if db.session.query(GLOpeningBatch.id).filter(
        GLOpeningBatch.status == "PENDING").first():
        return fail("Resolve pending opening balance imports before closing periods", 409)
    try:
        created = close_period(period, actor_id=user.id)
        if not created:
            return jsonify(period=period, status="ALREADY_CLOSED")
        audit(user, "gl.period_closed", "gl_period", period, reason=reason)
        db.session.commit()
    except (GLPostingError, ValueError) as exc:
        db.session.rollback()
        return fail(str(exc), 409)
    return jsonify(period=period,status="CLOSED",
                   warning="Closed GL periods refuse backdated postings; accountant review required.")


@gl_api.get("/finance/gl/<report_kind>.<file_type>")
@roles(*READERS)
def export_financial_report(_user, report_kind, file_type):
    """Bounded, role-protected accountant exports; never imply fiscal approval."""
    from io import BytesIO
    import xlsxwriter
    from ..report_exports import pdf_document, file_response
    if file_type not in ("pdf", "xlsx") or report_kind not in (
            "trial-balance", "balance-sheet", "income-statement"):
        abort(404)
    start,end=dates()
    property_id=optional_property()
    if report_kind=="trial-balance":
        report=trial_balance(through=end, property_id=property_id)
        headers=["Account","Name","Kind","Debit UGX","Credit UGX"]
        rows=[[item["code"],item["name"],item["kind"],
               item["debit_ugx"],item["credit_ugx"]] for item in report["accounts"]]
        rows.append(["TOTAL","","",report["debit_ugx"],report["credit_ugx"]])
        title="KATS General Ledger - Trial Balance"
    elif report_kind=="income-statement":
        report=income_statement(from_date=start,through=end,property_id=property_id)
        headers=["Account","Name","Classification","Amount UGX"]
        rows=[[item["code"],item["name"], "REVENUE",item["amount_ugx"]]
              for item in report["revenues"]]
        rows += [[item["code"],item["name"], "EXPENSE",item["amount_ugx"]]
                 for item in report["expenses"]]
        rows.append(["NET INCOME","","",report["net_income_ugx"]])
        title="KATS General Ledger - Income Statement"
    else:
        report=balance_sheet(through=end,property_id=property_id)
        headers=["Measure","Amount UGX"]
        rows=[[name,report[key]] for name,key in [
            ("Assets","assets_ugx"),("Liabilities","liabilities_ugx"),
            ("Equity","equity_ugx"),("Unclosed profit","unclosed_profit_ugx"),
            ("Difference","difference_ugx")]]
        title="KATS General Ledger - Balance Sheet"
    notice=("NEW GENERAL LEDGER EVENTS ONLY. Historical opening balances must "
            "be approved by an independent accountant. Not a URA fiscal document.")
    summary=["Currency: Uganda shillings (UGX)",notice,
             "Property: "+(property_id or "company-wide"),
             "Through: "+(end.isoformat() if end else "all posted events")]
    if file_type=="pdf":
        value=pdf_document(title,summary,
            headers=headers,rows=rows,
            footer="Internal accounting report, NOT proof of bank settlement or taxation.")
        return file_response(value,"application/pdf","kats-gl-"+report_kind+".pdf")
    stream=BytesIO()
    workbook=xlsxwriter.Workbook(stream, {"in_memory":True})
    worksheet=workbook.add_worksheet("KATS GL")
    heading=workbook.add_format({"bold":True,"bg_color":"#0B1B3D",
                                  "font_color":"#FFFFFF"})
    numeric=workbook.add_format({"num_format":"#,##0;[Red](#,##0)"})
    worksheet.write_string(0,0,title)
    for j,line in enumerate(summary,1):
        worksheet.write_string(j,0,line)
    header_row=len(summary)+2
    for col,label in enumerate(headers):
        worksheet.write_string(header_row,col,label,heading)
    for index,row in enumerate(rows,header_row+1):
        for col,value in enumerate(row):
            if type(value) is int:
                worksheet.write_number(index,col,value,numeric)
            else:
                worksheet.write_string(index,col,str(value))
    worksheet.freeze_panes(header_row+1,0)
    worksheet.set_column(0,1,24)
    worksheet.set_column(2,len(headers)-1,19)
    workbook.close()
    return file_response(
        stream.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "kats-gl-"+report_kind+".xlsx")
