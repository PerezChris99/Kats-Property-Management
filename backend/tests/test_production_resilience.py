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


def test_signed_cursor_pagination_does_not_duplicate_or_leak_history(app):
    from datetime import datetime, timezone
    from urllib.parse import quote
    owner = create_user("cursor-owner@kats.test", "OWNER")
    other = create_user("cursor-other@kats.test", "OWNER")
    prop = Property(name="Cursor test", address="Kampala", district="Kampala")
    db.session.add(prop)
    db.session.flush()
    room = Room(property_id=prop.id, number="C1", rent_ugx=250000)
    db.session.add(room)
    db.session.flush()
    same_time = datetime(2026, 11, 11, 11, 0, tzinfo=timezone.utc)
    for i in range(5):
        db.session.add(MaintenanceRequest(
            room_id=room.id, title=f"Ticket {i}",
            description="Pagination regression", priority="LOW",
            created_at=same_time))
    db.session.commit()
    owner_client = auth_client(app, owner)
    first = owner_client.get("/api/v1/maintenance?cursor=start&page_size=2")
    assert first.status_code == 200, first.json
    assert first.json["total"] is None
    assert len(first.json["items"]) == 2
    assert first.json["next_cursor"]
    cursor = first.json["next_cursor"]
    second = owner_client.get("/api/v1/maintenance?cursor=" + quote(cursor) + "&page_size=2")
    assert second.status_code == 200
    third = owner_client.get("/api/v1/maintenance?cursor=" + quote(second.json["next_cursor"]) + "&page_size=2")
    assert third.status_code == 200
    assert third.json["next_cursor"] is None
    ids = [v["id"] for row in (first, second, third) for v in row.json["items"]]
    assert len(ids) == len(set(ids)) == 5
    assert owner_client.get("/api/v1/maintenance?cursor="+quote(cursor)+"&page_size=3").status_code == 400
    assert owner_client.get("/api/v1/maintenance?cursor="+quote(cursor)+"t&page_size=2").status_code == 400
    other_client = auth_client(app, other)
    assert other_client.get("/api/v1/maintenance?cursor="+quote(cursor)+"&page_size=2").status_code == 400
    assert owner_client.get("/api/v1/properties?cursor=start").status_code == 400
    assert owner_client.get("/api/v1/maintenance?page=2&cursor=start").status_code == 400


def test_http_caching_only_applies_to_public_anonymous_read(client):
    public = client.get("/api/v1/public/landing-content")
    assert public.status_code == 200
    assert "max-age=60" in public.headers["Cache-Control"]
    etag = public.headers.get("ETag")
    assert etag
    not_modified = client.get("/api/v1/public/landing-content", headers={"If-None-Match": etag})
    assert not_modified.status_code == 304
    assert "public" in not_modified.headers["Cache-Control"]
    private = client.get("/api/v1/auth/me")
    assert private.status_code == 401
    assert private.headers["Cache-Control"] == "no-store"


def test_notification_cursor_returns_next_page_only_for_authenticated_owner(app):
    from datetime import datetime, timezone
    from urllib.parse import quote
    from app.extra_models import Notification
    user = create_user("notif-cursor@kats.test", "TENANT")
    other_user = create_user("notif-cursor-other@kats.test", "TENANT")
    fixed = datetime(2026, 11, 11, 11, 0, tzinfo=timezone.utc)
    for n in range(4):
        db.session.add(Notification(user_id=user.id, channel="IN_APP",
            kind="TEST", title=f"Notice {n}", body="Private update",
            status="PENDING", dedupe_key=f"notif-cursor-{n}", created_at=fixed))
    db.session.commit()
    client=auth_client(app,user)
    first=client.get("/api/v1/notifications?cursor=start&page_size=2")
    assert first.status_code == 200, first.json
    assert len(first.json["items"]) == 2
    assert first.json["next_cursor"] is not None
    second=client.get("/api/v1/notifications?cursor=" +
                      quote(first.json["next_cursor"]) + "&page_size=2")
    assert second.status_code == 200
    assert len(second.json["items"]) == 2
    assert second.json["next_cursor"] is None
    ids=[r["id"] for page in (first,second) for r in page.json["items"]]
    assert len(ids)==len(set(ids))==4
    other=auth_client(app,other_user)
    assert other.get("/api/v1/notifications?cursor=" +
        quote(first.json["next_cursor"]) + "&page_size=2").status_code==400
    assert other.get("/api/v1/notifications?cursor=start&page_size=2").json["items"]==[]
