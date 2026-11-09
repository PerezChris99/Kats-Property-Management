from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, RoomStateHistory
from conftest import create_user, auth_client, csrf

def test_caretaker_only_sees_assigned_rooms_and_cannot_approve_cash(app):
    owner = create_user("owner-caretaker@kats.test", "OWNER")
    caretaker = create_user("caretaker@kats.test", "CARETAKER")
    other = create_user("other-caretaker@kats.test", "CARETAKER")
    prop = Property(name="Caretaker Suites", address="Wakiso", district="Wakiso")
    db.session.add(prop)
    db.session.flush()
    first = Room(property_id=prop.id, number="1", rent_ugx=200000)
    second = Room(property_id=prop.id, number="2", rent_ugx=200000)
    tenant = Tenant(full_name="Test occupant", phone="+256700000333")
    db.session.add_all([first, second, tenant])
    db.session.flush()
    lease = Lease(room_id=first.id, tenant_id=tenant.id, start_date=date(2026, 11, 1),
                  end_date=date(2027, 11, 30), rent_ugx=200000)
    db.session.add(lease)
    db.session.flush()
    invoice = Invoice(invoice_number="KATS-TEST-CARE", lease_id=lease.id, tenant_id=tenant.id,
                      period_start=date(2026, 11, 1), period_end=date(2026, 11, 30),
                      due_date=date(2026, 11, 5), total_ugx=200000)
    db.session.add(invoice)
    db.session.commit()

    owner_client = auth_client(app, owner)
    caretaker_client = auth_client(app, caretaker)
    other_client = auth_client(app, other)
    assert caretaker_client.get("/api/v1/caretaker/rooms").json["total"] == 0
    assignment = owner_client.post("/api/v1/caretaker/assignments", headers=csrf(owner_client),
        json={"caretaker_user_id": caretaker.id, "room_id": first.id})
    assert assignment.status_code == 201, assignment.json
    assignment_id = assignment.json["assignment"]["id"]
    assert caretaker_client.get("/api/v1/caretaker/rooms").json["total"] == 1
    assert other_client.get("/api/v1/caretaker/rooms").json["total"] == 0
    assert caretaker_client.get("/api/v1/rooms").status_code == 403
    assert owner_client.get("/api/v1/caretaker/rooms").status_code == 403

    unassigned = caretaker_client.post("/api/v1/caretaker/maintenance", headers=csrf(caretaker_client),
        json={"room_id": second.id, "title": "Leaking sink", "description": "Pipe leaking"})
    assert unassigned.status_code == 403
    assigned = caretaker_client.post("/api/v1/caretaker/maintenance", headers=csrf(caretaker_client),
        json={"room_id": first.id, "title": "Leaking sink", "description": "Pipe leaking"})
    assert assigned.status_code == 201, assigned.json
    assert caretaker_client.get("/api/v1/caretaker/maintenance").json["total"] == 1
    state = caretaker_client.post("/api/v1/caretaker/rooms/" + first.id + "/status",
        headers=csrf(caretaker_client), json={"status":"MAINTENANCE","reason":"Major leak"})
    assert state.status_code == 200, state.json
    assert db.session.query(RoomStateHistory).filter_by(room_id=first.id).count() == 1

    submission = {"invoice_id": invoice.id, "amount_ugx": 60000, "idempotency_key": "care-0001"}
    pending = caretaker_client.post("/api/v1/caretaker/payments", headers=csrf(caretaker_client), json=submission)
    assert pending.status_code == 201, pending.json
    assert db.session.get(Invoice, invoice.id).paid_ugx == 0
    payment_id = pending.json["payment"]["id"]
    assert caretaker_client.post("/api/v1/payments/" + payment_id + "/approve",
                                  headers=csrf(caretaker_client)).status_code == 403
    assert owner_client.post("/api/v1/payments/" + payment_id + "/approve",
                             headers=csrf(owner_client)).status_code == 200
    assert db.session.get(Invoice, invoice.id).paid_ugx == 60000
    assert caretaker_client.get("/api/v1/caretaker/payments").json["total"] == 1
    removed = owner_client.delete("/api/v1/caretaker/assignments/" + assignment_id,
                                  headers=csrf(owner_client))
    assert removed.status_code == 200
    assert caretaker_client.get("/api/v1/caretaker/rooms").json["total"] == 0
    assert caretaker_client.post("/api/v1/caretaker/payments", headers=csrf(caretaker_client),
        json={"invoice_id": invoice.id, "amount_ugx": 10000, "idempotency_key": "care-0002"}).status_code == 403

def test_cookie_csrf_protection_on_changes(app):
    owner = create_user("csrf-owner@kats.test", "OWNER")
    client = auth_client(app, owner)
    assert client.post("/api/v1/properties", json={
        "name": "Should fail", "address": "Kampala", "district": "Kampala"
    }).status_code == 401
