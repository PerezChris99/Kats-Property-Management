"""Audited user data-access/correction/restriction request register.

Financial/audit information is not deleted automatically. Retention decisions
require a legally approved business policy and independent human review.
"""
from .extensions import db
from .models import new_id, utcnow, CheckConstraint

class PrivacyRequest(db.Model):
    __tablename__ = "privacy_requests"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    requester_user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    tenant_id = db.Column(db.String(36), db.ForeignKey("tenants.id", ondelete="RESTRICT"))
    kind = db.Column(db.String(25), nullable=False)
    details = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(25), nullable=False, default="SUBMITTED")
    decision_notes = db.Column(db.Text)
    reviewed_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        CheckConstraint("kind IN ('ACCESS','RECTIFY','ERASURE','RESTRICT','OBJECT')", name="ck_privacy_request_kind"),
        CheckConstraint("status IN ('SUBMITTED','IN_REVIEW','COMPLETED','DECLINED')", name="ck_privacy_request_state"),
        db.Index("ix_privacy_requests_status_created","status","created_at"),
    )
