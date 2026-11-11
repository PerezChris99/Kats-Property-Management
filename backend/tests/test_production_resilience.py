"""Recover interrupted maintenance operations without duplicate work tickets."""
from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, MaintenanceRequest
from conftest import create_user, auth_client, csrf


def test_maintenance_create_is_idempotent_and_actor_scoped(app):
    owner = create_user("maintenance-idempotency-owner@kats.test", "OWNER")
    tenant_user = create_user("maintenance-idempotency-tenant@kats.test", "TENANT")
    prop = Property(name="Test building", address="Kampala", district="Kampala")
    db.session.add(prop)
    db.session.flush()
    room = Room(property_id=prop.id, number="L-03", status="OCCUPIED",
                rent_ugx=200000)
    tenant = Tenant(user_id=tenant_user.id, full_name="One tenant",
                    phone="+256700123000")
    db.session.add_all([room, tenant])
    db.session.flush()
    db.session.add(Lease(room_id=room.id, tenant_id=tenant.id,
                         start_date=date(2026, 1, 1), end_date=date(2028, 1, 1),
                         rent_ugx=200000))
    db.session.commit()
    first = auth_client(app, tenant_user)
    body = {"room_id": room.id, "title": "Leaking tap", "description": "Kitchen tap dripping",
            "priority": "MEDIUM", "idempotency_key": "offline-create-0001"}
    response = first.post("/api/v1/maintenance", json=body, headers=csrf(first))
    assert response.status_code == 201
    replay = first.post("/api/v1/maintenance", json=body, headers=csrf(first))
    assert replay.status_code == 200
    assert replay.json["reused"] is True
    assert replay.json["request"]["id"] == response.json["request"]["id"]
    assert db.session.query(MaintenanceRequest).count() == 1
    different = {**body, "title": "Different problem"}
    conflict = first.post("/api/v1/maintenance", json=different, headers=csrf(first))
    assert conflict.status_code == 409
    invalid = {**body, "idempotency_key": "../../../../../"}
    assert first.post("/api/v1/maintenance", json=invalid, headers=csrf(first)).status_code == 400
    # A separate authorized actor can reuse the same client command without
    # viewing or changing the tenant's original request.
    owner_client = auth_client(app, owner)
    another = owner_client.post("/api/v1/maintenance", json=body,
                                headers=csrf(owner_client))
    assert another.status_code == 201
    assert db.session.query(MaintenanceRequest).count() == 2


def test_tenants_cannot_create_other_unit_work_even_with_idempotency_key(app):
    user = create_user("unlinked-idempotent@kats.test", "TENANT")
    prop = Property(name="Other unit", address="Wakiso", district="Wakiso")
    db.session.add(prop)
    db.session.flush()
    room = Room(property_id=prop.id, number="R1", rent_ugx=400000)
    db.session.add(room)
    db.session.commit()
    client = auth_client(app, user)
    response = client.post("/api/v1/maintenance", json={
        "room_id": room.id, "title": "Try", "description": "Unauthorized room",
        "idempotency_key": "other-room-001"
    }, headers=csrf(client))
    assert response.status_code == 403
    assert db.session.query(MaintenanceRequest).count() == 0


def test_celery_scope_cannot_leak_to_another_task():
    from app.document_rls import _SCOPE
    from app.tasks import KATSServicedTask
    class Probe(KATSServicedTask):
        def run(self):
            return _SCOPE.get()
    assert _SCOPE.get() is None
    context = Probe()()
    assert context["role"] == "SERVICE"
    assert context["tenant_id"] == ""
    assert _SCOPE.get() is None
