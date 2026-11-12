"""Balanced new-receipt journal, idempotence and non-fabricated legacy reversals."""
from sqlalchemy import func
from app.extensions import db
from app.models import Payment
from app.journal import post_receipt_journal
from app.journal_models import JournalEvent, JournalLine
from test_workspace_analytics import seeded


def test_journal_records_atomic_balanced_receipt_and_reversal(app,monkeypatch):
    seeded(app,monkeypatch)
    payment = db.session.query(Payment).filter_by(status="RECONCILED").first()
    assert payment is not None
    assert post_receipt_journal(payment) is True
    assert post_receipt_journal(payment) is False
    db.session.commit()
    receipt = db.session.query(JournalEvent).filter_by(event_key="receipt:"+payment.id).one()
    lines = db.session.query(JournalLine).filter_by(event_id=receipt.id).all()
    assert len(lines)==2
    assert sum(row.debit_ugx for row in lines)==sum(row.credit_ugx for row in lines)==payment.amount_ugx
    assert {row.account_code for row in lines}=={"CASH_CLEARING","RENT_RECEIVABLE"}

    assert post_receipt_journal(payment,reverse=True) is True
    assert post_receipt_journal(payment,reverse=True) is False
    db.session.commit()
    reversal=db.session.query(JournalEvent).filter_by(event_key="reversal:"+payment.id).one()
    reverse_lines=db.session.query(JournalLine).filter_by(event_id=reversal.id).all()
    assert sum(row.debit_ugx for row in reverse_lines)==sum(row.credit_ugx for row in reverse_lines)==payment.amount_ugx
    assert {(line.account_code,line.debit_ugx>0) for line in reverse_lines}=={
        ("RENT_RECEIVABLE",True),("CASH_CLEARING",False)}


def test_legacy_unjournaled_reversal_does_not_create_negative_cash(app,monkeypatch):
    seeded(app,monkeypatch)
    payment=db.session.query(Payment).filter_by(status="RECONCILED").first()
    assert payment
    assert post_receipt_journal(payment,reverse=True) is False
    db.session.commit()
    assert db.session.query(JournalEvent).count()==0
