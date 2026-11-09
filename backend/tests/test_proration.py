from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, InvoiceLine, LedgerEntry
from conftest import create_user, auth_client, csrf

def build_lease(start,end,rent):
    p=Property(name="Rent",address="Kampala",district="Kampala")
    db.session.add(p);db.session.flush()
    r=Room(property_id=p.id,number="PR-1",rent_ugx=rent,status="OCCUPIED")
    t=Tenant(full_name="Tenant",phone="+256700009988")
    db.session.add_all([r,t]);db.session.flush()
    lease=Lease(room_id=r.id,tenant_id=t.id,start_date=start,end_date=end,
                rent_ugx=rent)
    db.session.add(lease);db.session.commit()
    return lease.id

def test_proration_preview_issuance_and_replay_prevention(app):
    owner=create_user("prorate-owner@kats.test","OWNER")
    tenant=create_user("prorate-tenant@kats.test","TENANT")
    lease_id=build_lease(date(2026,11,11),date(2026,11,20),300000)
    client=auth_client(app,owner)
    preview=client.get("/api/v1/billing/proration/preview?lease_id="+lease_id+"&month=2026-11")
    assert preview.status_code==200,preview.json
    assert preview.json["preview"]["days_in_month"]==30
    assert preview.json["preview"]["amount_ugx"]==100000
    params={"lease_id":lease_id,"month":"2026-11","due_date":"2026-11-15",
            "policy":"ACTUAL_CALENDAR_DAYS","confirm_policy":True,"reason":"Approved lease terms"}
    refused=client.post("/api/v1/billing/proration/issue",json={**params,"confirm_policy":False},
        headers=csrf(client))
    assert refused.status_code==400
    created=client.post("/api/v1/billing/proration/issue",json=params,headers=csrf(client))
    assert created.status_code==201,created.json
    assert created.json["invoice"]["total_ugx"]==100000
    again=client.post("/api/v1/billing/proration/issue",json=params,headers=csrf(client))
    assert again.status_code==409
    invoice=db.session.get(Invoice,created.json["invoice"]["id"])
    lines=db.session.query(InvoiceLine).filter_by(invoice_id=invoice.id).all()
    assert len(lines)==1 and lines[0].amount_ugx==100000
    assert db.session.query(LedgerEntry).filter_by(invoice_id=invoice.id).count()==1
    alien=auth_client(app,tenant)
    assert alien.get("/api/v1/billing/proration/preview?lease_id="+lease_id+"&month=2026-11").status_code==403

def test_effective_dated_rent_proration_midmonth(app):
    owner=create_user("prorate-owner-2@kats.test","OWNER")
    lease_id=build_lease(date(2026,1,1),date(2026,11,15),300000)
    cli=auth_client(app,owner)
    updated=cli.post("/api/v1/leases/"+lease_id+"/renew",headers=csrf(cli),json={
        "new_end_date":"2027-11-30","new_rent_ugx":180000,"reason":"Renewal signed"})
    assert updated.status_code==201,updated.json
    preview=cli.get("/api/v1/billing/proration/preview?lease_id="+lease_id+"&month=2026-11")
    assert preview.status_code==200,preview.json
    calculated=preview.json["preview"]
    assert len(calculated["segments"])==2
    assert calculated["segments"][0]["amount_ugx"]==150000
    assert calculated["segments"][1]["amount_ugx"]==90000
    assert calculated["amount_ugx"]==240000
    created=cli.post("/api/v1/billing/proration/issue",headers=csrf(cli),json={
        "lease_id":lease_id,"month":"2026-11","due_date":"2026-11-20",
        "policy":"ACTUAL_CALENDAR_DAYS","confirm_policy":True,"reason":"Signed monthly proration"})
    assert created.status_code==201,created.json
    assert created.json["invoice"]["total_ugx"]==240000
