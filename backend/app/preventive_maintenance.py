"""Bounded automatic preventive-maintenance request generation."""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from .extensions import db
from .models import MaintenanceRequest,AuditLog
from .maintenance_plan_models import MaintenancePlan,MaintenanceOccurrence
from .billing import system_actor

def generate_due_maintenance(today=None):
    today=today or datetime.now(ZoneInfo("Africa/Kampala")).date()
    actor=system_actor()
    cursor=""
    created=0
    while True:
        # Each plan is locked so duplicate Celery tasks cannot generate a
        # second occurrence for the same scheduled date.
        plans=(db.session.query(MaintenancePlan).filter(
            MaintenancePlan.status=="ACTIVE",
            MaintenancePlan.next_due_on<=today,
            MaintenancePlan.id>cursor)
            .order_by(MaintenancePlan.id)
            .limit(100).with_for_update().all())
        if not plans:break
        cursor=plans[-1].id
        for plan in plans:
            scheduled=plan.next_due_on
            if db.session.query(MaintenanceOccurrence.id).filter_by(
                    plan_id=plan.id,scheduled_for=scheduled).first():
                # Heal stale schedule pointer after interrupted earlier run.
                while plan.next_due_on<=today:
                    plan.next_due_on+=timedelta(days=plan.cadence_days)
                continue
            request=MaintenanceRequest(room_id=plan.room_id,tenant_id=None,
                title="Scheduled: "+plan.title,description=plan.instructions,
                priority=plan.priority,status="OPEN")
            db.session.add(request)
            db.session.flush()
            db.session.add(MaintenanceOccurrence(plan_id=plan.id,
                scheduled_for=scheduled,maintenance_request_id=request.id))
            db.session.add(AuditLog(actor_id=actor.id,
                action="maintenance.preventive_created",target_type="maintenance_request",
                target_id=request.id,
                details={"plan_id":plan.id,"scheduled_for":scheduled.isoformat()}))
            while plan.next_due_on<=today:
                plan.next_due_on+=timedelta(days=plan.cadence_days)
            created+=1
        db.session.commit()
    return {"generated":created,"as_of":today.isoformat()}
