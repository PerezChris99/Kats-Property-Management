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
