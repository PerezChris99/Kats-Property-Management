"""Preventive maintenance scales without an occurrence SELECT per plan."""
from datetime import date
from sqlalchemy import event
from app.extensions import db
from app.models import Property, Room, MaintenanceRequest
from app.maintenance_plan_models import MaintenancePlan, MaintenanceOccurrence
from app.preventive_maintenance import generate_due_maintenance
from conftest import create_user


def test_due_plan_batch_uses_one_occurrence_lookup_and_is_idempotent(app):
    owner = create_user("maintenance-scale-owner@kats.test", "OWNER")
    property_ = Property(name="Batch Tower", address="Kampala", district="Kampala")
    db.session.add(property_)
    db.session.flush()
    room = Room(property_id=property_.id, number="BATCH", status="OCCUPIED", rent_ugx=250000)
    db.session.add(room)
    db.session.flush()
    day = date(2026, 11, 10)
    db.session.add_all([
        MaintenancePlan(room_id=room.id, created_by=owner.id,
                        title=f"Scheduled check {index}", instructions="Check equipment",
                        priority="LOW", cadence_days=7, next_due_on=day)
        for index in range(50)
    ])
    db.session.commit()

    queries = []
    def inspect_sql(_connection, _cursor, statement, _parameters, _context, _executemany):
        if (statement.lstrip().upper().startswith("SELECT")
                and "maintenance_occurrences" in statement):
            queries.append(statement)

    event.listen(db.engine, "before_cursor_execute", inspect_sql)
    try:
        result = generate_due_maintenance(day)
    finally:
        event.remove(db.engine, "before_cursor_execute", inspect_sql)
    assert result["generated"] == 50, result
    assert len(queries) <= 2, f"N+1 occurrence lookup regression: {len(queries)} SELECTs"
    assert db.session.query(MaintenanceOccurrence).count() == 50
    assert db.session.query(MaintenanceRequest).filter(
        MaintenanceRequest.title.like("Scheduled: Scheduled check%")).count() == 50

    again = generate_due_maintenance(day)
    assert again["generated"] == 0
    assert db.session.query(MaintenanceOccurrence).count() == 50
