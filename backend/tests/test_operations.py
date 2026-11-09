from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, MaintenanceRequest
from app.extra_models import Notification, LegalPage, FiscalSubmission, WorkOrder
from app.notifications import rent_reminder_run
from conftest import create_user, auth_client, csrf

def test_legal_version_publication_and_user_visibility(app):
    owner = create_user("legalowner@kats.test", "OWNER")
    tenant = create_user("legaltenant@kats.test", "TENANT")
    admin = auth_client(app, owner)
    visitor = app.test_client()
    assert visitor.get("/api/v1/public/legal/privacy").status_code == 404
    created = admin.post("/api/v1/admin/legal-pages",headers=csrf(admin),
        json={"slug":"privacy","title":"Privacy Policy","content":"Our approved policy v1"})
    assert created.status_code == 201, created.json
    assert created.json["page"]["version"] == 1
    assert visitor.get("/api/v1/public/legal/privacy").status_code == 404
    page_id=created.json["page"]["id"]
    publish=admin.post("/api/v1/admin/legal-pages/"+page_id+"/publish",headers=csrf(admin))
    assert publish.status_code == 200
    public=visitor.get("/api/v1/public/legal/privacy")
    assert public.status_code == 200 and public.json["page"]["content"] == "Our approved policy v1"
    low=auth_client(app,tenant)
    assert low.get("/api/v1/admin/legal-pages").status_code == 403
    assert low.post("/api/v1/admin/legal-pages", headers=csrf(low),json={
        "slug":"privacy","title":"Hijacked","content":"Bad"}).status_code == 403

def test_notifications_are_idempotent_and_private(app):
    owner=create_user("notify-owner@kats.test", "OWNER")
    user=create_user("notify-tenant@kats.test", "TENANT")
    other=create_user("notify-other@kats.test", "TENANT")
    prop=Property(name="Kats Rent", address="Kampala", district="Kampala")
    db.session.add(prop)
    db.session.flush()
    room=Room(property_id=prop.id,number="N1",rent_ugx=100000,status="OCCUPIED")
    tenant=Tenant(user_id=user.id,full_name="Notify",phone="+256700002222")
    db.session.add_all([room,tenant])
    db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=tenant.id,start_date=date(2026,1,1),
                end_date=date(2027,1,1),rent_ugx=100000)
    db.session.add(lease)
    db.session.flush()
    inv=Invoice(invoice_number="KATS-NOTIFY",lease_id=lease.id,tenant_id=tenant.id,
                period_start=date(2026,11,1),period_end=date(2026,11,30),
                due_date=date(2026,11,9),total_ugx=100000)
    db.session.add(inv)
    db.session.commit()
    first=rent_reminder_run(date(2026,11,9))
    assert first["notified"] == 1
    second=rent_reminder_run(date(2026,11,9))
    assert second["notified"] == 0
    assert db.session.query(Notification).count() == 1
    account=auth_client(app,user)
    messages=account.get("/api/v1/notifications")
    assert messages.status_code == 200 and messages.json["total"] == 1
    note_id=messages.json["items"][0]["id"]
    stranger=auth_client(app,other)
    assert stranger.get("/api/v1/notifications").json["total"] == 0
    assert stranger.post("/api/v1/notifications/"+note_id+"/read",
        headers=csrf(stranger)).status_code == 404
    assert account.post("/api/v1/notifications/"+note_id+"/read",
        headers=csrf(account)).status_code == 200

def test_efris_queue_never_falsely_claims_fiscal_success(app):
    owner=create_user("efris-owner@kats.test","OWNER")
    tenant=create_user("efris-tenant@kats.test","TENANT")
    prop=Property(name="Kats",address="Kampala",district="Kampala")
    db.session.add(prop); db.session.flush()
    room=Room(property_id=prop.id,number="5",rent_ugx=120000,status="OCCUPIED")
    occupant=Tenant(full_name="Occupant",phone="+256700003333")
    db.session.add_all([room,occupant]);db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=occupant.id,start_date=date(2026,1,1),
                end_date=date(2027,1,1),rent_ugx=120000)
    db.session.add(lease);db.session.flush()
    invoice=Invoice(invoice_number="KATS-FISCAL",lease_id=lease.id,tenant_id=occupant.id,
                    period_start=date(2026,11,1),period_end=date(2026,11,30),
                    due_date=date(2026,11,9),total_ugx=120000)
    issue=MaintenanceRequest(room_id=room.id,title="Leak",description="Water leak")
    db.session.add_all([invoice,issue]); db.session.commit()
    staff=auth_client(app,owner)
    first=staff.post("/api/v1/efris/queue",headers=csrf(staff),json={"invoice_id":invoice.id})
    assert first.status_code == 202,first.json
    assert first.json["submission"]["state"] == "PENDING_FISCALIZATION"
    again=staff.post("/api/v1/efris/queue",headers=csrf(staff),json={"invoice_id":invoice.id})
    assert again.status_code == 200
    assert db.session.query(FiscalSubmission).count() == 1
    outsider=auth_client(app,tenant)
    assert outsider.get("/api/v1/efris").status_code == 403
    blocked=outsider.post("/api/v1/efris/queue",headers=csrf(outsider),
                         json={"invoice_id":invoice.id})
    assert blocked.status_code == 403
    work=staff.post("/api/v1/maintenance/"+issue.id+"/work-orders",headers=csrf(staff),
        json={"scope":"Replace leaking tap","estimated_cost_ugx":30000})
    assert work.status_code == 201,work.json
    assert db.session.query(WorkOrder).count() == 1

def test_storage_missing_fails_closed(app):
    user=create_user("docs-owner@kats.test","OWNER")
    cli=auth_client(app,user)
    res=cli.post("/api/v1/documents/presign",headers=csrf(cli),json={
        "category":"LEASE","mime_type":"application/pdf","filename":"lease.pdf","size_bytes":1200
    })
    assert res.status_code == 503
