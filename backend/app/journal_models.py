"""Balanced event journal for newly verified rent receipts.

This is a *posting bridge*, not yet a complete accrual general ledger.
An event is posted once in the same transaction as its source payment.
Historical invoices/expenses require independently reviewed backfill.
"""
from .extensions import db
from .models import new_id, utcnow

class JournalEvent(db.Model):
    __tablename__ = "journal_events"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    event_key = db.Column(db.String(160), unique=True, nullable=False)
    source_payment_id = db.Column(db.String(36), db.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False)
    posted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (db.CheckConstraint("kind IN ('RECEIPT', 'REVERSAL')", name="ck_journal_event_kind"),)

class JournalLine(db.Model):
    __tablename__ = "journal_lines"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    event_id = db.Column(db.String(36), db.ForeignKey("journal_events.id", ondelete="RESTRICT"), nullable=False, index=True)
    account_code = db.Column(db.String(40), nullable=False)
    debit_ugx = db.Column(db.BigInteger, nullable=False, default=0)
    credit_ugx = db.Column(db.BigInteger, nullable=False, default=0)
    __table_args__ = (
        db.CheckConstraint("debit_ugx >= 0 AND credit_ugx >= 0", name="ck_journal_nonnegative"),
        db.CheckConstraint("(debit_ugx > 0 AND credit_ugx = 0) OR (credit_ugx > 0 AND debit_ugx = 0)", name="ck_journal_one_side"),
        db.UniqueConstraint("event_id","account_code",name="uq_journal_account_per_event")
    )
