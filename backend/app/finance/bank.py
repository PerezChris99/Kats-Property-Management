"""UGX bank statement reconciliation against actual independently reviewed GL.

Statement CSV ingestion only records bank-supplied evidence. It cannot claim
that funds were sent/received or that an uploaded file is authentic. Incoming
bank deposits transfer previously verified CASH_CLEARING to BANK only after a
second person approves allocations totalling the bank statement line.
"""
from __future__ import annotations
import csv
import hashlib
import io
import re
from datetime import date, timedelta
from sqlalchemy import func, or_
from ..extensions import db
from .ledger import GLPostingError, post_event
from .gl_models import GLEvent, GLLine
from .bank_models import BankStatement, BankStatementLine, BankMatch

LIMIT = 10**15
MAX_ROWS = 3000


class BankEvidenceError(ValueError):
    pass


def parse_amount(value: str):
    if not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9][0-9]{0,14})", value):
        raise BankEvidenceError("Bank amounts must be unsigned integer Uganda shillings")
    number = int(value)
    if number > LIMIT:
        raise BankEvidenceError("Bank amount exceeds safe UGX limit")
    return number


def parse_bank_csv(content: str, start: date, end: date):
    """Strict, bounded CSV; never infer amount, dates, or sign conventions."""
    if not isinstance(content, str) or not 25 <= len(content) <= 1024 * 1024:
        raise BankEvidenceError("Bank CSV is missing or too large")
    try:
        csv_reader = csv.DictReader(io.StringIO(content, newline=""), strict=True)
        if csv_reader.fieldnames != [
            "date", "reference", "description", "inflow_ugx", "outflow_ugx"
        ]:
            raise BankEvidenceError(
                "CSV columns must be date,reference,description,inflow_ugx,outflow_ugx")
        rows = []
        for record in csv_reader:
            if len(rows) >= MAX_ROWS or None in record or None in record.values():
                raise BankEvidenceError("Too many rows or inconsistent bank columns")
            try:
                booked = date.fromisoformat(record["date"])
            except ValueError as exc:
                raise BankEvidenceError("Every statement date must use YYYY-MM-DD") from exc
            if not start <= booked <= end:
                raise BankEvidenceError("Bank transaction falls outside statement period")
            credit, debit = parse_amount(record["inflow_ugx"]), parse_amount(record["outflow_ugx"])
            if (credit == 0) == (debit == 0):
                raise BankEvidenceError("A bank row needs exactly one nonzero inflow or outflow")
            ref, desc = record["reference"].strip(), record["description"].strip()
            if (len(ref) > 160 or len(desc) > 500 or any(
                    ord(c) < 32 for c in ref + desc)):
                raise BankEvidenceError("Invalid bank reference or description")
            rows.append((booked, ref, desc, credit - debit))
    except (csv.Error, TypeError, AttributeError) as exc:
        raise BankEvidenceError("Invalid bank CSV format") from exc
    if not rows:
        raise BankEvidenceError("A bank statement must contain at least one transaction")
    return rows


def import_statement(*, bank_label: str, account_mask: str, start: date, end: date,
                     opening: int, closing: int, csv_text: str, actor_id: str):
    if (not 1 <= len(bank_label) <= 120 or
            not 4 <= len(account_mask) <= 30 or
            not account_mask.startswith("*") or
            any(ord(c) < 32 for c in bank_label + account_mask)):
        raise BankEvidenceError("Bank label and masked account reference required")
    if type(opening) is not int or type(closing) is not int or max(abs(opening), abs(closing)) > LIMIT:
        raise BankEvidenceError("Opening/closing bank balances must be integer UGX")
    if start > end:
        raise BankEvidenceError("Bank statement start cannot exceed end")
    rows = parse_bank_csv(csv_text, start, end)
    if opening + sum(row[-1] for row in rows) != closing:
        raise BankEvidenceError("Statement inflow/outflow totals do not reconcile to closing balance")
    fingerprint = hashlib.sha256(
        repr((bank_label, account_mask, start.isoformat(), end.isoformat(),
              opening, closing, rows)).encode("utf-8")
    ).hexdigest()
    if db.session.query(BankStatement.id).filter_by(content_sha256=fingerprint).first():
        raise BankEvidenceError("Bank statement already imported; inspect original evidence")
    batch = BankStatement(
        bank_label=bank_label, account_mask=account_mask,
        start_date=start, end_date=end, opening_ugx=opening,
        closing_ugx=closing, content_sha256=fingerprint, imported_by=actor_id,
        state="OPEN")
    db.session.add(batch)
    db.session.flush()
    db.session.add_all([
        BankStatementLine(statement_id=batch.id, row_number=index, booked_on=booked,
                          reference=ref, description=desc, signed_ugx=signed)
        for index, (booked, ref, desc, signed) in enumerate(rows, 1)])
    return batch


def cash_delta(event_id: str, code: str) -> int:
    return int(db.session.query(func.coalesce(func.sum(
        GLLine.debit_ugx - GLLine.credit_ugx), 0)).filter(
        GLLine.event_id == event_id, GLLine.account_code == code).scalar() or 0)


def eligible_source(event: GLEvent, signed: int) -> int:
    if event.kind in ("BANK_SETTLEMENT", "OPENING_BALANCES"):
        return 0
    code = "CASH_CLEARING" if signed > 0 else "BANK"
    value = cash_delta(event.id, code)
    if value == 0 or (value > 0) != (signed > 0):
        return 0
    return value


def approved_amount_for_line(line_id: str):
    return int(db.session.query(func.coalesce(func.sum(BankMatch.signed_ugx), 0)).filter(
        BankMatch.statement_line_id == line_id, BankMatch.state == "APPROVED").scalar() or 0)


def approved_amount_for_event(event_id: str):
    return int(db.session.query(func.coalesce(func.sum(BankMatch.signed_ugx), 0)).filter(
        BankMatch.gl_event_id == event_id, BankMatch.state == "APPROVED").scalar() or 0)


def propose_match(*, line: BankStatementLine, event: GLEvent,
                  amount: int, maker: str):
    if db.session.get(BankStatement, line.statement_id).state != "OPEN":
        raise BankEvidenceError("A closed bank statement cannot be modified")
    if type(amount) is not int or amount == 0 or abs(amount) > LIMIT:
        raise BankEvidenceError("Match requires a signed nonzero integer UGX allocation")
    if (amount > 0) != (line.signed_ugx > 0):
        raise BankEvidenceError("Bank and ledger transaction directions differ")
    if abs((event.posted_on - line.booked_on).days) > 14:
        raise BankEvidenceError("Source date differs by over 14 days; manual adjustment needed")
    value = eligible_source(event, amount)
    if not value or abs(amount) > abs(value):
        raise BankEvidenceError("GL event has no eligible cash/bank entry")
    if db.session.query(BankMatch.id).filter_by(
            statement_line_id=line.id, gl_event_id=event.id).first():
        raise BankEvidenceError("This source was already matched or proposed on that row")
    if abs(approved_amount_for_line(line.id) + amount) > abs(line.signed_ugx):
        raise BankEvidenceError("Bank statement row would be over-matched")
    if abs(approved_amount_for_event(event.id) + amount) > abs(value):
        raise BankEvidenceError("GL source would be over-allocated")
    match = BankMatch(statement_line_id=line.id, gl_event_id=event.id,
                      signed_ugx=amount, state="PROPOSED", proposed_by=maker)
    db.session.add(match)
    return match


def approve_match(match: BankMatch, reviewer: str):
    from datetime import datetime, timezone
    line = db.session.query(BankStatementLine).filter_by(id=match.statement_line_id).with_for_update().one()
    statement = db.session.query(BankStatement).filter_by(id=line.statement_id).with_for_update().one()
    event = db.session.query(GLEvent).filter_by(id=match.gl_event_id).with_for_update().one()
    if statement.state != "OPEN" or match.state != "PROPOSED":
        raise BankEvidenceError("Bank review is no longer pending")
    if reviewer in (match.proposed_by, statement.imported_by):
        raise BankEvidenceError("Independent bank statement review required")
    value = eligible_source(event, match.signed_ugx)
    if not value:
        raise BankEvidenceError("GL source is no longer eligible")
    if abs(approved_amount_for_event(event.id) + match.signed_ugx) > abs(value):
        raise BankEvidenceError("GL source is already allocated")
    completed = approved_amount_for_line(line.id) + match.signed_ugx
    if abs(completed) > abs(line.signed_ugx):
        raise BankEvidenceError("Statement row would be over-allocated")
    match.state = "APPROVED"
    match.reviewed_by = reviewer
    match.reviewed_at = datetime.now(timezone.utc)
    if completed == line.signed_ugx and completed > 0:
        # No book recognition before a distinct checker approves the WHOLE
        # bank deposit. This is a transfer only, not new income or cash.
        post_event(
            "bank-settlement:" + line.id, "BANK_SETTLEMENT", line.booked_on,
            [("BANK", completed, 0), ("CASH_CLEARING", 0, completed)],
            actor_id=reviewer)
    return completed


def bank_book_balance(through: date, *, before=False):
    query = db.session.query(func.coalesce(
        func.sum(GLLine.debit_ugx - GLLine.credit_ugx), 0)).join(
        GLEvent, GLEvent.id == GLLine.event_id).filter(
        GLLine.account_code == "BANK")
    query = query.filter(GLEvent.posted_on < through if before else
                         GLEvent.posted_on <= through)
    return int(query.scalar() or 0)


def reconcile_report(statement: BankStatement):
    lines = db.session.query(BankStatementLine).filter_by(
        statement_id=statement.id).order_by(BankStatementLine.row_number).all()
    outstanding, pending, matched = [], [], []
    for item in lines:
        approved = approved_amount_for_line(item.id)
        proposed = db.session.query(BankMatch.id).filter_by(
            statement_line_id=item.id, state="PROPOSED").count()
        status = ("MATCHED" if approved == item.signed_ugx else
                  "PARTIAL" if approved else "UNMATCHED")
        row = {
            "id": item.id,
            "row_number": item.row_number,
            "booked_on": item.booked_on.isoformat(),
            "reference": item.reference, "description": item.description,
            "signed_ugx": item.signed_ugx,
            "approved_ugx": approved,
            "unmatched_ugx": item.signed_ugx - approved,
            "status": status, "pending_proposals": proposed,
        }
        if status == "MATCHED":
            matched.append(row)
        else:
            outstanding.append(row)
        if proposed:
            pending.append(row)
    book_open = bank_book_balance(statement.start_date, before=True)
    book_close = bank_book_balance(statement.end_date)
    return {
        "statement": {
            "id":statement.id,"bank_label":statement.bank_label,
            "account_mask":statement.account_mask,
            "start_date":statement.start_date.isoformat(),
            "end_date":statement.end_date.isoformat(),
            "state":statement.state,
            "opening_ugx":statement.opening_ugx,
            "closing_ugx":statement.closing_ugx,
            "imported_by":statement.imported_by,
        },
        "book_opening_ugx": book_open,
        "book_closing_ugx": book_close,
        "opening_difference_ugx": book_open - statement.opening_ugx,
        "closing_difference_ugx": book_close - statement.closing_ugx,
        "matched": matched, "exceptions": outstanding,
        "pending_reviews": pending,
        "can_close": (
            not outstanding and not pending and
            book_open == statement.opening_ugx and
            book_close == statement.closing_ugx),
        "scope": "SINGLE_BOOK_BANK_ACCOUNT",
        "warning": "Operator-imported bank CSV is not proof of independent bank confirmation. No payment provider was instructed to transfer funds.",
    }
