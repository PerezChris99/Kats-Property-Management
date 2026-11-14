"""Atomic, idempotent, company-level double-entry posting in integer UGX.

This is the canonical NEW-event general ledger, separate from the historical
receipt-only journal. Historical invoices/payments MUST be approved and
backfilled as balanced opening balances; never silently fabricate history.
All methods join the caller's transaction; no implicit commits.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
from zoneinfo import ZoneInfo
from sqlalchemy import func, text
from ..extensions import db
from ..models import Lease, Room, Invoice, Payment, Expense, DepositMovement
from .accounts import DEFAULT_ACCOUNTS, INVOICE_REVENUE, EXPENSE_ACCOUNTS
from .gl_models import GLAccount, GLEvent, GLLine, GLPeriodClose

KAMPALA = ZoneInfo("Africa/Kampala")
LIMIT = 10**15


class GLPostingError(ValueError):
    pass


def today() -> date:
    return datetime.now(KAMPALA).date()


def ensure_chart():
    """Create absent defaults for SQLite unit fixtures; migrations seed production."""
    existing = {row[0] for row in db.session.query(GLAccount.code).all()}
    if len(existing) == len(DEFAULT_ACCOUNTS) and all(code in existing for code, _, _ in DEFAULT_ACCOUNTS):
        return
    for code, title, kind in DEFAULT_ACCOUNTS:
        if code not in existing:
            db.session.add(GLAccount(code=code, name=title, kind=kind))
    db.session.flush()


def period_lock(period: str):
    if db.session.get_bind().dialect.name == "postgresql":
        # Close and posting serialize on the same transaction-scoped lock.
        # Lock the company/period, never a per-user or per-property surrogate.
        db.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                           {"key": "kats:gl:" + period})


def validate_lines(lines: list[tuple[str, int, int]]):
    if not isinstance(lines, (list, tuple)) or not 2 <= len(lines) <= 200:
        raise GLPostingError("General ledger requires two to 200 lines")
    total_dr = total_cr = 0
    normalized = []
    allowed = {code for code, _, _ in DEFAULT_ACCOUNTS}
    for item in lines:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise GLPostingError("Each line requires account, debit and credit")
        code, dr, cr = item
        if code not in allowed or type(dr) is not int or type(cr) is not int:
            raise GLPostingError("Unsupported GL account or noninteger UGX amount")
        if not (0 <= dr <= LIMIT and 0 <= cr <= LIMIT and (dr == 0) != (cr == 0)):
            raise GLPostingError("Exactly one positive debit/credit per line is required")
        total_dr += dr
        total_cr += cr
        normalized.append((code, dr, cr))
    if total_dr != total_cr or not 0 < total_dr <= LIMIT:
        raise GLPostingError("Unbalanced journal posting")
    return normalized


def post_event(event_key: str, kind: str, posted_on: date,
               lines: list[tuple[str, int, int]], *,
               property_id: str | None = None, actor_id: str | None = None) -> bool:
    """Create immutable event and balanced lines, without committing caller txn."""
    if (not isinstance(event_key, str) or not 1 <= len(event_key) <= 160 or
            not isinstance(kind, str) or not 1 <= len(kind) <= 40 or
            not isinstance(posted_on, date) or isinstance(posted_on, datetime)):
        raise GLPostingError("Invalid GL source identity or posting date")
    clean = validate_lines(lines)
    payload = [kind, posted_on.isoformat(), property_id, clean]
    digest = hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()
    previous = db.session.query(GLEvent).filter_by(event_key=event_key).first()
    if previous:
        if previous.fingerprint != digest:
            raise GLPostingError("GL idempotency source replay has changed transaction details")
        return False
    period = posted_on.strftime("%Y-%m")
    period_lock(period)
    if db.session.get(GLPeriodClose, period):
        raise GLPostingError("Posting period is closed; a separately approved current-period adjustment is required")
    ensure_chart()
    event = GLEvent(event_key=event_key, kind=kind, posted_on=posted_on,
                    property_id=property_id, actor_id=actor_id, fingerprint=digest)
    db.session.add(event)
    db.session.flush()
    db.session.add_all([
        GLLine(event_id=event.id, account_code=code, debit_ugx=debit, credit_ugx=credit)
        for code, debit, credit in clean
    ])
    return True


def invoice_property(invoice: Invoice) -> str | None:
    return db.session.query(Room.property_id).join(
        Lease, Lease.room_id == Room.id).filter(Lease.id == invoice.lease_id).scalar()


def post_invoice(invoice: Invoice, line_amounts: list[tuple[str, int]], *, actor_id=None):
    grouped = defaultdict(int)
    for kind, amount in line_amounts:
        code = INVOICE_REVENUE.get(kind)
        if code is None or type(amount) is not int or amount < 0:
            raise GLPostingError("Unknown invoice charge type/amount for accounting")
        grouped[code] += amount
    if sum(grouped.values()) != invoice.total_ugx:
        raise GLPostingError("Invoice GL amount differs from invoice total")
    if invoice.total_ugx == 0:
        # A zero-value invoice has no economic posting; no artificial entry.
        return False
    return post_event("invoice:" + invoice.id, "INVOICE_ACCRUAL",
                      invoice.period_start,
                      [("RENT_RECEIVABLE", invoice.total_ugx, 0)] +
                      [(code, 0, amount) for code, amount in sorted(grouped.items()) if amount],
                      property_id=invoice_property(invoice), actor_id=actor_id)


def post_utility(reading, invoice: Invoice, *, actor_id=None):
    amount = reading.charge_ugx
    if type(amount) is not int or amount <= 0:
        raise GLPostingError("Utility posting requires an approved positive charge")
    return post_event("utility:" + reading.id, "UTILITY_BILL",
                      reading.observed_on,
                      [("RENT_RECEIVABLE", amount, 0), ("UTILITY_RECOVERY", 0, amount)],
                      property_id=invoice_property(invoice), actor_id=actor_id)


def post_payment(payment: Payment, invoice: Invoice, *, actor_id=None):
    if payment.status != "RECONCILED" or payment.settled_at is None:
        raise GLPostingError("Unverified payments cannot enter the general ledger")
    amount = payment.amount_ugx
    return post_event("payment:" + payment.id, "RECEIPT",
                      payment.settled_at.date(),
                      [("CASH_CLEARING", amount, 0), ("RENT_RECEIVABLE", 0, amount)],
                      property_id=invoice_property(invoice), actor_id=actor_id)


def post_credit(note, invoice: Invoice, *, actor_id=None):
    amount = note.amount_ugx
    # Credit notes may cover mixed charge types. Until explicit credit-line
    # allocation is approved, use a segregated contra-revenue account.
    return post_event("credit:" + note.id, "CREDIT_NOTE",
                      today(),
                      [("REVENUE_CREDITS", amount, 0), ("RENT_RECEIVABLE", 0, amount)],
                      property_id=invoice_property(invoice), actor_id=actor_id)


def reverse_posted(source_key: str, reversal_key: str, kind: str, *,
                   actor_id=None) -> bool:
    """Compensate a NEW, posted event; refuse to invent legacy reverse history."""
    original = db.session.query(GLEvent).filter_by(event_key=source_key).first()
    if original is None:
        return False
    rows = db.session.query(GLLine).filter_by(event_id=original.id).order_by(GLLine.id).all()
    return post_event(reversal_key, kind, today(),
                      [(row.account_code, row.credit_ugx, row.debit_ugx) for row in rows],
                      property_id=original.property_id, actor_id=actor_id)


def post_expense(expense: Expense, *, reverse=False, actor_id=None):
    code = EXPENSE_ACCOUNTS.get(expense.category.upper(), "OTHER_EXPENSE")
    amount = expense.amount_ugx
    if reverse:
        return reverse_posted("expense:" + expense.id,
                              "expense-reverse:" + expense.id, "EXPENSE_REVERSAL",
                              actor_id=actor_id)
    return post_event("expense:" + expense.id, "EXPENSE_ACCRUAL", expense.incurred_on,
                      [(code, amount, 0), ("ACCOUNTS_PAYABLE", 0, amount)],
                      property_id=expense.property_id, actor_id=actor_id)


def post_deposit(movement: DepositMovement, *, actor_id=None):
    if movement.status != "APPROVED":
        raise GLPostingError("Unapproved deposit movement is not a GL event")
    lease = db.session.get(Lease, movement.lease_id)
    if not lease:
        raise GLPostingError("Deposit lease is missing")
    property_id = db.session.query(Room.property_id).filter(Room.id == lease.room_id).scalar()
    amount = movement.amount_ugx
    if movement.kind == "HOLD":
        debit, credit = "CASH_CLEARING", "TENANT_DEPOSITS"
    elif movement.kind == "REFUND":
        # Approval is NOT proof of actual payout; record a refund liability
        # rather than incorrectly reducing the BANK/CASH account.
        debit, credit = "TENANT_DEPOSITS", "DEPOSIT_REFUNDS_PAYABLE"
    elif movement.kind == "WITHHOLD":
        debit, credit = "TENANT_DEPOSITS", "OTHER_INCOME"
    else:
        raise GLPostingError("Unsupported deposit movement")
    when = movement.reviewed_at.date() if movement.reviewed_at else today()
    return post_event("deposit:" + movement.id, "DEPOSIT_" + movement.kind, when,
                      [(debit, amount, 0), (credit, 0, amount)],
                      property_id=property_id, actor_id=actor_id)


def close_period(period: str, *, actor_id: str):
    if not isinstance(period, str) or not len(period) == 7:
        raise GLPostingError("Period must use YYYY-MM")
    try:
        parsed = date.fromisoformat(period + "-01")
    except ValueError as exc:
        raise GLPostingError("Period must use YYYY-MM") from exc
    if parsed >= today().replace(day=1):
        raise GLPostingError("Current or future financial periods may not be closed")
    period_lock(period)
    if db.session.get(GLPeriodClose, period):
        return False
    # The database constraint guarantees each event balances. Verify control
    # totals on actual persisted lines before accepting a permanent closure.
    dr, cr = db.session.query(func.coalesce(func.sum(GLLine.debit_ugx), 0),
                              func.coalesce(func.sum(GLLine.credit_ugx), 0)).join(
        GLEvent, GLEvent.id == GLLine.event_id).filter(
        GLEvent.posted_on < date(parsed.year + (parsed.month == 12),
                                1 if parsed.month == 12 else parsed.month + 1, 1)).one()
    if int(dr) != int(cr):
        raise GLPostingError("Cannot close period with unbalanced ledger")
    db.session.add(GLPeriodClose(period=period, closed_by=actor_id))
    return True
