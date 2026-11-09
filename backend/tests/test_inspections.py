from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Inspection, RoomStateHistory
from conftest import create_user, auth_client, csrf

def test_termination_requires_inspection_and_retains_room_history(app):
    manager = create_user("inspections-manager@kats.test", "MANAGER")
    tenant_user = create_user("inspections-tenant@kats.test", "TENANT")
    prop = Property(name="Lease Building", address="Kampala", district="Kampala")
    db.session.add(prop)
    db.session.flush()
    room = Room(property_id=prop.id, number="R1", rent_ugx=150000, status="OCCUPIED")
    tenant = Tenant(user_id=tenant_user.id, full_name="Tenant", phone="+256780000000")
    db.session.add_all([room, tenant])
    db.session.flush()
    lease = Lease(room_id=room.id, tenant_id=tenant.id, start_date=date(2026, 1, 1),
                  end_date=date(2027, 1, 1), rent_ugx=150000)
    db.session.add(lease)
    db.session.commit()

    staff = auth_client(app, manager)
    outsider = auth_client(app, tenant_user)
    assert staff.post("/api/v1/leases/" + lease.id + "/terminate",
        headers=csrf(staff), json={"reason": "Tenant moved out"}).status_code == 409
    assert outsider.post("/api/v1/inspections", headers=csrf(outsider),
        json={"lease_id": lease.id,"kind":"MOVE_OUT","observed_on":"2026-11-09",
              "condition_notes":"Inspection done"}).status_code == 403
    entry = staff.post("/api/v1/inspections", headers=csrf(staff),
        json={"lease_id":lease.id, "kind":"MOVE_OUT", "observed_on":"2026-11-09",
              "condition_notes":"Paint damage recorded", "damage_estimate_ugx":25000})
    assert entry.status_code == 201, entry.json
    inspections = outsider.get("/api/v1/inspections")
    assert inspections.status_code == 200 and inspections.json["total"] == 1
    terminated = staff.post("/api/v1/leases/" + lease.id + "/terminate",
        headers=csrf(staff), json={"reason":"Inspection reviewed and keys returned"})
    assert terminated.status_code == 200, terminated.json
    assert terminated.json["room"]["status"] == "CLEANING"
    assert db.session.get(Lease, lease.id).status == "TERMINATED"
    assert db.session.query(RoomStateHistory).filter_by(room_id=room.id).count() == 1
    again = staff.post("/api/v1/leases/" + lease.id + "/terminate",
        headers=csrf(staff), json={"reason":"Repeated command"})
    assert again.status_code == 200
    assert db.session.query(RoomStateHistory).filter_by(room_id=room.id).count() == 1
