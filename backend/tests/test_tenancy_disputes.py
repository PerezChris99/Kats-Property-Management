from datetime import date
from app.extensions import db
from app.models import Property,Room,Tenant,Lease
from app.dispute_models import TenancyDispute,DisputeEvent
from conftest import create_user,auth_client,csrf

def test_tenant_dispute_scoping_and_independent_disposition(app):
    owner=create_user("disputes-owner@kats.test","OWNER")
    alice=create_user("disputes-alice@kats.test","TENANT")
    stranger=create_user("disputes-bob@kats.test","TENANT")
    p=Property(name="Kampala House",address="Ntinda",district="Kampala")
    db.session.add(p);db.session.flush()
    room=Room(property_id=p.id,number="D1",rent_ugx=200000,status="OCCUPIED")
    tenant=Tenant(user_id=alice.id,full_name="Alice",phone="256700002200")
    db.session.add_all([room,tenant]);db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=tenant.id,start_date=date(2026,1,1),
                end_date=date(2027,12,31),rent_ugx=200000,deposit_ugx=200000)
    db.session.add(lease);db.session.commit()
    ca=auth_client(app,alice)
    cb=auth_client(app,stranger)
    co=auth_client(app,owner)
    opened=ca.post("/api/v1/disputes",headers=csrf(ca),json={
        "lease_id":lease.id,"kind":"DEPOSIT","title":"Deposit deduction challenged",
        "description":"Please explain the proposed damage deduction with evidence."})
    assert opened.status_code==201,opened.json
    dispute_id=opened.json["dispute"]["id"]
    assert cb.get("/api/v1/disputes").json["items"]==[]
    assert cb.get("/api/v1/disputes/"+dispute_id+"/events").status_code==404
    assert cb.post("/api/v1/disputes/"+dispute_id+"/comments",headers=csrf(cb),
        json={"comment":"Cross-tenant record"}).status_code==404
    assert ca.post("/api/v1/disputes/"+dispute_id+"/decision",headers=csrf(ca),
        json={"status":"RESOLVED","reason":"Owner only"}).status_code==403
    assert ca.post("/api/v1/disputes/"+dispute_id+"/comments",headers=csrf(ca),
        json={"comment":"Original check-out photographs are attached to the case file."}).status_code==201
    changed=co.post("/api/v1/disputes/"+dispute_id+"/decision",headers=csrf(co),
        json={"status":"IN_REVIEW","reason":"Accountant reviewing condition report"})
    assert changed.status_code==200
    resolved=co.post("/api/v1/disputes/"+dispute_id+"/decision",headers=csrf(co),
        json={"status":"RESOLVED","reason":"Decision and evidence delivered separately"})
    assert resolved.status_code==200
    closed=ca.post("/api/v1/disputes/"+dispute_id+"/comments",headers=csrf(ca),
        json={"comment":"A follow-up is needed"}).status_code
    assert closed==409
    assert len(ca.get("/api/v1/disputes/"+dispute_id+"/events").json["items"])==4
    assert db.session.query(TenancyDispute).count()==1
    assert db.session.query(DisputeEvent).count()==4
