"""Tenancy dispute register and non-destructive event history."""
from .extensions import db
from .models import new_id, utcnow, CheckConstraint

class TenancyDispute(db.Model):
    __tablename__ = "tenancy_disputes"
    id = db.Column(db.String(36),primary_key=True,default=new_id)
    lease_id = db.Column(db.String(36),db.ForeignKey("leases.id",ondelete="RESTRICT"),nullable=False,index=True)
    tenant_id = db.Column(db.String(36),db.ForeignKey("tenants.id",ondelete="RESTRICT"),nullable=False,index=True)
    kind = db.Column(db.String(24),nullable=False)
    title = db.Column(db.String(160),nullable=False)
    description = db.Column(db.Text,nullable=False)
    status = db.Column(db.String(24),nullable=False,default="OPEN")
    opened_by = db.Column(db.String(36),db.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False)
    reviewed_by = db.Column(db.String(36),db.ForeignKey("users.id",ondelete="RESTRICT"))
    created_at = db.Column(db.DateTime(timezone=True),nullable=False,default=utcnow,index=True)
    updated_at = db.Column(db.DateTime(timezone=True),nullable=False,default=utcnow)
    closed_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("kind IN ('RENT','DEPOSIT','REPAIR','SERVICE','NOTICE','OTHER')",name="ck_dispute_kind"),
        CheckConstraint("status IN ('OPEN','IN_REVIEW','RESOLVED','DECLINED')",name="ck_dispute_status"),
        db.Index("ix_tenancy_disputes_status_created","status","created_at"),
    )

class DisputeEvent(db.Model):
    __tablename__ = "dispute_events"
    id = db.Column(db.String(36),primary_key=True,default=new_id)
    dispute_id = db.Column(db.String(36),db.ForeignKey("tenancy_disputes.id",ondelete="RESTRICT"),nullable=False,index=True)
    actor_id = db.Column(db.String(36),db.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False)
    event = db.Column(db.String(32),nullable=False)
    comment = db.Column(db.Text,nullable=False)
    previous_status = db.Column(db.String(24))
    new_status = db.Column(db.String(24))
    created_at = db.Column(db.DateTime(timezone=True),nullable=False,default=utcnow,index=True)
