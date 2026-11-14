"""Immutable canonical double-entry ledger; legacy receipt bridge is separate."""
from ..extensions import db
from ..models import new_id, utcnow

class GLAccount(db.Model):
    __tablename__ = "gl_accounts"
    code = db.Column(db.String(40), primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    kind = db.Column(db.String(15), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (
        db.CheckConstraint("kind IN ('ASSET','LIABILITY','EQUITY','REVENUE','EXPENSE')",
                           name="ck_gl_account_kind"),
    )

class GLEvent(db.Model):
    __tablename__ = "gl_events"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    event_key = db.Column(db.String(160), nullable=False, unique=True)
    kind = db.Column(db.String(40), nullable=False)
    posted_on = db.Column(db.Date, nullable=False, index=True)
    property_id = db.Column(db.String(36), db.ForeignKey("properties.id", ondelete="RESTRICT"),
                            nullable=True, index=True)
    actor_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"))
    fingerprint = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

class GLLine(db.Model):
    __tablename__ = "gl_lines"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    event_id = db.Column(db.String(36), db.ForeignKey("gl_events.id", ondelete="RESTRICT"),
                         nullable=False, index=True)
    account_code = db.Column(db.String(40), db.ForeignKey("gl_accounts.code", ondelete="RESTRICT"),
                             nullable=False, index=True)
    debit_ugx = db.Column(db.BigInteger, nullable=False, default=0)
    credit_ugx = db.Column(db.BigInteger, nullable=False, default=0)
    __table_args__ = (
        db.CheckConstraint("debit_ugx >= 0 AND credit_ugx >= 0", name="ck_gl_nonnegative"),
        db.CheckConstraint(
            "(debit_ugx > 0 AND credit_ugx = 0) OR (credit_ugx > 0 AND debit_ugx = 0)",
            name="ck_gl_one_sided_line"),
    )

class GLPeriodClose(db.Model):
    __tablename__ = "gl_period_closures"
    period = db.Column(db.String(7), primary_key=True)
    closed_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"),
                          nullable=False)
    closed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

class GLOpeningBatch(db.Model):
    __tablename__ = "gl_opening_batches"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    import_sha256 = db.Column(db.String(64), nullable=False, unique=True)
    effective_on = db.Column(db.Date, nullable=False)
    rows = db.Column(db.JSON, nullable=False)
    note = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(15), nullable=False, default="PENDING")
    submitted_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    approved_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    approved_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (
        db.CheckConstraint("status IN ('PENDING','POSTED','REJECTED')", name="ck_gl_opening_status"),
    )
