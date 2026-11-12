"""Atomic accounting bridge for receipts and reversals.

Entries represent cash clearing versus an existing receivable. They are NOT
external bank settlement, or recognition of all accrual invoice revenue.
"""
from .extensions import db
from .journal_models import JournalEvent, JournalLine


def post_receipt_journal(payment, *, reverse=False):
    """Add exactly two balanced lines without committing; caller owns transaction.

    The source Payment is already locked by the financial mutation flow.
    Duplicate events are prevented by event_key's database uniqueness.
    """
    if payment.amount_ugx <= 0:
        raise ValueError("Cannot post non-positive payment")
    kind = "REVERSAL" if reverse else "RECEIPT"
    key = kind.lower() + ":" + payment.id
    if db.session.query(JournalEvent.id).filter_by(event_key=key).first():
        return False
    event = JournalEvent(event_key=key, source_payment_id=payment.id, kind=kind)
    db.session.add(event)
    db.session.flush()
    amount = payment.amount_ugx
    debit = "RENT_RECEIVABLE" if reverse else "CASH_CLEARING"
    credit = "CASH_CLEARING" if reverse else "RENT_RECEIVABLE"
    db.session.add(JournalLine(event_id=event.id, account_code=debit, debit_ugx=amount, credit_ugx=0))
    db.session.add(JournalLine(event_id=event.id, account_code=credit, debit_ugx=0, credit_ugx=amount))
    return True
