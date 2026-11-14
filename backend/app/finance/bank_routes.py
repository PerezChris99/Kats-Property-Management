"""Bank evidence imports, exception queue and maker-checker reconciliation APIs.

These APIs never connect to a banking network or claim a payout succeeded.
Only independent accounting approvals can transfer cleared receipts into BANK.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from flask import Blueprint, abort, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from ..api import audit, data, fail, required_string, roles
from ..extensions import db
from .bank import (
    BankEvidenceError, import_statement, eligible_source, propose_match,
    approve_match, reconcile_report, approved_amount_for_event, bank_book_balance,
)
from .bank_models import BankStatement, BankStatementLine, BankMatch
from .gl_models import GLEvent, GLLine

bank_api = Blueprint("bank_reconciliation", __name__)
REVIEWERS = ("OWNER", "ACCOUNTANT", "SUPER_ADMIN")


def signed_int(obj, field):
    value = obj.get(field)
    if type(value) is not int or abs(value) > 10**15:
        raise BankEvidenceError(field + " must be a bounded integer Uganda-shilling amount")
    return value


def statement_query(statement_id, lock=False):
    query = db.session.query(BankStatement).filter_by(id=statement_id)
    if lock:
        query = query.with_for_update()
    statement = query.first()
    if not statement:
        abort(404)
    return statement


@bank_api.post("/finance/bank-statements")
@roles(*REVIEWERS)
def upload_statement(user):
    obj = data()
    try:
        start = date.fromisoformat(required_string(obj, "start_date", 10))
        end = date.fromisoformat(required_string(obj, "end_date", 10))
        label = required_string(obj, "bank_label", 120)
        masked = required_string(obj, "account_mask", 30)
        opening = signed_int(obj, "opening_ugx")
        closing = signed_int(obj, "closing_ugx")
        statement = import_statement(
            bank_label=label, account_mask=masked, start=start, end=end,
            opening=opening, closing=closing, csv_text=obj.get("csv_text", ""),
            actor_id=user.id)
        audit(user, "bank.statement_import", "bank_statement", statement.id,
              rows_count=db.session.query(BankStatementLine.id).filter_by(
                  statement_id=statement.id).count(),
              sha256=statement.content_sha256)
        db.session.commit()
    except (BankEvidenceError, ValueError) as exc:
        db.session.rollback()
        return fail(str(exc), 400)
    except IntegrityError:
        db.session.rollback()
        return fail("Bank statement duplicate or inconsistent import", 409)
    return jsonify(statement_id=statement.id, state="OPEN",
                   notice="Imported bank statement evidence only; matching requires independent review."), 201


@bank_api.get("/finance/bank-statements")
@roles(*REVIEWERS)
def list_statements(_user):
    rows = db.session.query(BankStatement).order_by(
        BankStatement.imported_at.desc()).limit(100).all()
    return jsonify(items=[
        {"id":s.id,"bank_label":s.bank_label,"account_mask":s.account_mask,
         "start_date":s.start_date.isoformat(),"end_date":s.end_date.isoformat(),
         "state":s.state,"closing_ugx":s.closing_ugx}
        for s in rows])


@bank_api.get("/finance/bank-statements/<statement_id>")
@roles(*REVIEWERS)
def get_statement(_user, statement_id):
    return jsonify(reconcile_report(statement_query(statement_id)))


@bank_api.get("/finance/bank-statements/<statement_id>/matches")
@roles(*REVIEWERS)
def list_matches(_user, statement_id):
    statement_query(statement_id)
    rows = db.session.query(BankMatch).join(
        BankStatementLine, BankStatementLine.id == BankMatch.statement_line_id
    ).filter(BankStatementLine.statement_id == statement_id).order_by(
        BankMatch.created_at.desc()).limit(500).all()
    return jsonify(items=[
        {"id":match.id,"line_id":match.statement_line_id,
         "event_id":match.gl_event_id,"signed_ugx":match.signed_ugx,
         "state":match.state,"proposed_by":match.proposed_by,
         "reviewed_by":match.reviewed_by}
        for match in rows])


@bank_api.get("/finance/bank-statements/<statement_id>/candidates/<line_id>")
@roles(*REVIEWERS)
def bank_candidates(_user, statement_id, line_id):
    statement_query(statement_id)
    line = db.session.query(BankStatementLine).filter_by(
        id=line_id, statement_id=statement_id).first()
    if not line:
        abort(404)
    from_date = line.booked_on.fromordinal(line.booked_on.toordinal() - 14)
    to_date = line.booked_on.fromordinal(line.booked_on.toordinal() + 14)
    code = "CASH_CLEARING" if line.signed_ugx > 0 else "BANK"
    entries = db.session.query(GLEvent).join(
        GLLine, GLLine.event_id == GLEvent.id).filter(
        GLLine.account_code == code,
        GLEvent.posted_on >= from_date, GLEvent.posted_on <= to_date,
        GLEvent.kind.notin_(("BANK_SETTLEMENT", "OPENING_BALANCES"))
    ).distinct().order_by(GLEvent.posted_on.desc()).limit(100).all()
    found = []
    for event in entries:
        amount = eligible_source(event, line.signed_ugx)
        available = abs(amount) - abs(approved_amount_for_event(event.id))
        if available <= 0:
            continue
        found.append({
            "id":event.id,"event_key":event.event_key,"kind":event.kind,
            "date":event.posted_on.isoformat(),"available_ugx":available,
            "signed_ugx":amount,
            "days_apart":abs((event.posted_on-line.booked_on).days),
        })
    found.sort(key=lambda x: (x["days_apart"], -min(x["available_ugx"],abs(line.signed_ugx))))
    return jsonify(items=found[:25], warning="Suggestions are not automatic payment settlement evidence.")


@bank_api.post("/finance/bank-statements/<statement_id>/matches")
@roles(*REVIEWERS)
def create_match(user, statement_id):
    obj = data()
    statement = statement_query(statement_id, lock=True)
    line = db.session.query(BankStatementLine).filter_by(
        id=required_string(obj,"line_id"),statement_id=statement.id).with_for_update().first()
    if not line:
        abort(404)
    event = db.session.query(GLEvent).filter_by(
        id=required_string(obj,"gl_event_id")).with_for_update().first()
    if not event:
        abort(404)
    try:
        amount = signed_int(obj,"signed_ugx")
        match = propose_match(line=line,event=event,amount=amount,maker=user.id)
        db.session.flush()
        audit(user,"bank.match_proposed","bank_match",match.id,
              statement_line_id=line.id,gl_event_id=event.id,amount_ugx=amount)
        db.session.commit()
    except BankEvidenceError as exc:
        db.session.rollback()
        return fail(str(exc),409)
    except IntegrityError:
        db.session.rollback()
        return fail("Match was already proposed",409)
    return jsonify(match_id=match.id,state="PROPOSED",
                   notice="Awaiting independent checker approval."),201


@bank_api.post("/finance/bank-matches/<match_id>/review")
@roles(*REVIEWERS)
def review_match(user, match_id):
    obj = data()
    decision = required_string(obj,"decision",20).upper()
    reason = required_string(obj,"reason",500)
    if decision not in ("APPROVE","REJECT"):
        return fail("Invalid bank match decision",400)
    match = db.session.query(BankMatch).filter_by(id=match_id).with_for_update().first()
    if not match:
        abort(404)
    if match.state != "PROPOSED":
        return fail("Match has already been reviewed",409)
    line = db.session.get(BankStatementLine,match.statement_line_id)
    statement = db.session.get(BankStatement,line.statement_id)
    if user.id in (match.proposed_by,statement.imported_by):
        return fail("Bank match requires a different statement importer/proposer",403)
    try:
        if decision == "APPROVE":
            completed = approve_match(match,user.id)
        else:
            if statement.state != "OPEN":
                return fail("Cannot reject match on closed statement",409)
            completed = 0
            match.state = "REJECTED"
            match.reviewed_by = user.id
            match.reviewed_at = datetime.now(timezone.utc)
        audit(user,"bank.match_review","bank_match",match.id,decision=decision,
              reason=reason,approved_row_ugx=completed)
        db.session.commit()
    except (BankEvidenceError, ValueError) as exc:
        db.session.rollback()
        return fail(str(exc),409)
    return jsonify(match_id=match.id,state=match.state,
                   notice="Bank evidence review recorded. No external funds were moved.")


@bank_api.post("/finance/bank-statements/<statement_id>/close")
@roles(*REVIEWERS)
def close_statement(user,statement_id):
    reason=required_string(data(),"reason",500)
    statement=statement_query(statement_id,lock=True)
    if statement.state=="RECONCILED":
        return jsonify(state="RECONCILED",reconciled=True)
    if user.id==statement.imported_by:
        return fail("Bank statement close requires independent finance reviewer",403)
    result=reconcile_report(statement)
    if not result["can_close"]:
        return jsonify(error={
            "code":"BANK_RECONCILIATION_OPEN",
            "message":"Unmatched evidence or ledger balance difference",
        },report=result),409
    statement.state="RECONCILED"
    statement.closed_by=user.id
    statement.closed_at=datetime.now(timezone.utc)
    audit(user,"bank.statement_closed","bank_statement",statement.id,
          reason=reason,ending_balance_ugx=statement.closing_ugx)
    db.session.commit()
    return jsonify(state=statement.state,reconciled=True,
                   warning="Review uploaded source authenticity outside the application; this is accounting reconciliation only.")
