"""Explicit, two-person reviewed reconciliation against imported bank statements.

Only an uploaded, bank-authenticated statement can authorize external
reconciliation. Matching never treats mobile-money initiation as settlement.
Bank statement rows may be grouped; approval of the full signed amount creates
an atomic CASH_CLEARING -> BANK transfer for deposits, or merely validates an
already booked BANK credit for disbursements.
"""
from ..extensions import db
from ..models import new_id, utcnow

class BankStatement(db.Model):
    __tablename__ = "bank_statements"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    bank_label = db.Column(db.String(120), nullable=False)
    account_mask = db.Column(db.String(30), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    opening_ugx = db.Column(db.BigInteger, nullable=False)
    closing_ugx = db.Column(db.BigInteger, nullable=False)
    content_sha256 = db.Column(db.String(64), nullable=False, unique=True)
    state = db.Column(db.String(20), nullable=False, default="OPEN")
    imported_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    closed_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"))
    imported_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    closed_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (
        db.CheckConstraint("state IN ('OPEN','RECONCILED')", name="ck_bank_statement_state"),
        db.CheckConstraint("end_date >= start_date", name="ck_bank_statement_dates"),
    )

class BankStatementLine(db.Model):
    __tablename__ = "bank_statement_lines"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    statement_id = db.Column(db.String(36), db.ForeignKey("bank_statements.id", ondelete="RESTRICT"), nullable=False, index=True)
    row_number = db.Column(db.Integer, nullable=False)
    booked_on = db.Column(db.Date, nullable=False)
    reference = db.Column(db.String(160), nullable=False, default="")
    description = db.Column(db.String(500), nullable=False, default="")
    signed_ugx = db.Column(db.BigInteger, nullable=False)
    __table_args__ = (
        db.UniqueConstraint("statement_id", "row_number", name="uq_bank_statement_row"),
        db.CheckConstraint("signed_ugx <> 0", name="ck_bank_line_nonzero"),
    )

class BankMatch(db.Model):
    __tablename__ = "bank_reconciliation_matches"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    statement_line_id = db.Column(db.String(36), db.ForeignKey("bank_statement_lines.id", ondelete="RESTRICT"), nullable=False, index=True)
    gl_event_id = db.Column(db.String(36), db.ForeignKey("gl_events.id", ondelete="RESTRICT"), nullable=False, index=True)
    signed_ugx = db.Column(db.BigInteger, nullable=False)
    state = db.Column(db.String(15), nullable=False, default="PROPOSED")
    proposed_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reviewed_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        db.UniqueConstraint("statement_line_id", "gl_event_id", name="uq_bank_match_source"),
        db.CheckConstraint("signed_ugx <> 0", name="ck_bank_match_nonzero"),
        db.CheckConstraint("state IN ('PROPOSED','APPROVED','REJECTED')", name="ck_bank_match_state"),
    )
