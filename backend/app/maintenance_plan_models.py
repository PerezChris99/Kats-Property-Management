"""Recurring preventive-maintenance plans and immutable generated occurrences."""
from .extensions import db
from .models import new_id,utcnow,CheckConstraint

class MaintenancePlan(db.Model):
    __tablename__="maintenance_plans"
    id=db.Column(db.String(36),primary_key=True,default=new_id)
    room_id=db.Column(db.String(36),db.ForeignKey("rooms.id",ondelete="RESTRICT"),nullable=False,index=True)
    title=db.Column(db.String(120),nullable=False)
    instructions=db.Column(db.Text,nullable=False)
    priority=db.Column(db.String(20),nullable=False,default="MEDIUM")
    cadence_days=db.Column(db.Integer,nullable=False)
    next_due_on=db.Column(db.Date,nullable=False,index=True)
    status=db.Column(db.String(20),nullable=False,default="ACTIVE")
    created_by=db.Column(db.String(36),db.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=utcnow)
    updated_at=db.Column(db.DateTime(timezone=True),nullable=False,default=utcnow)
    __table_args__=(
        CheckConstraint("cadence_days BETWEEN 1 AND 366",name="ck_maintenance_plan_cadence"),
        CheckConstraint("priority IN ('LOW','MEDIUM','HIGH','URGENT')",name="ck_maintenance_plan_priority"),
        CheckConstraint("status IN ('ACTIVE','PAUSED','RETIRED')",name="ck_maintenance_plan_status"),
        db.Index("ix_maintenance_plans_due_status","status","next_due_on"),
    )

class MaintenanceOccurrence(db.Model):
    __tablename__="maintenance_occurrences"
    id=db.Column(db.String(36),primary_key=True,default=new_id)
    plan_id=db.Column(db.String(36),db.ForeignKey("maintenance_plans.id",ondelete="RESTRICT"),nullable=False,index=True)
    scheduled_for=db.Column(db.Date,nullable=False)
    maintenance_request_id=db.Column(db.String(36),db.ForeignKey("maintenance_requests.id",ondelete="RESTRICT"),nullable=False,unique=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=utcnow)
    __table_args__=(
        db.UniqueConstraint("plan_id","scheduled_for",name="uq_maintenance_plan_occurrence"),
    )
