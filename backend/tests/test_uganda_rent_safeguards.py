from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice
from conftest import create_user, auth_client, csrf

def fixture_records(app):
    owner=create_user("uganda-rent-owner@kats.test","OWNER")
    tenant_user=create_user("uganda-rent-tenant@kats.test","TENANT")
    prop=Property(name="Wakiso Apartments",address="Wakiso",district="Wakiso")
    db.session.add(prop);db.session.flush()
    room=Room(property_id=prop.id,number="1A",status="VACANT",rent_ugx=150000,deposit_ugx=150000)
    tenant=Tenant(full_name="Occupant",phone="256700000000",user_id=tenant_user.id)
    db.session.add_all([room,tenant]);db.session.commit()
    return owner,tenant_user,room,tenant,prop

def test_one_month_deposit_cap_and_required_lease_terms(app):
    owner,tenant_user,room,tenant,_=fixture_records(app)
    cli=auth_client(app,owner)
    body={"room_id":room.id,"tenant_id":tenant.id,"start_date":"2026-01-01",
          "end_date":"2027-12-31","rent_ugx":150000,"deposit_ugx":150000}
    assert cli.post("/api/v1/leases",headers=csrf(cli),json={**body,"deposit_ugx":150001}).status_code==409
    assert cli.post("/api/v1/leases",headers=csrf(cli),json={**body,"deposit_ugx":-1}).status_code==400
    # Uganda law caps a demanded deposit but does not require a landlord to
    # collect one at all. Zero-deposit tenancies must remain possible.
    assert cli.post("/api/v1/leases",headers=csrf(cli),json={**body,"deposit_ugx":0}).status_code==201

def test_notice_linked_rent_increase_rejects_no_notice_and_over_cap(app):
    owner,tenant_user,room,tenant,_=fixture_records(app)
    room.status="OCCUPIED"
    lease=Lease(room_id=room.id,tenant_id=tenant.id,start_date=date(2026,1,1),
                end_date=date(2026,12,31),rent_ugx=150000,deposit_ugx=150000)
    db.session.add(lease);db.session.commit()
    cli=auth_client(app,owner)
    rent={"new_end_date":"2027-12-31","new_rent_ugx":165000,"reason":"Renewal"}
    assert cli.post("/api/v1/leases/"+lease.id+"/renew",headers=csrf(cli),json=rent).status_code==409
    notice={"notice_type":"RENT_INCREASE","served_on":"2026-10-01",
            "effective_on":"2027-01-01","proposed_rent_ugx":165000,
            "delivery_method":"EMAIL","delivery_reference":"smtp-tracking-1",
            "reason":"Verified 60-day notice"}
    created=cli.post("/api/v1/leases/"+lease.id+"/notices",headers=csrf(cli),json=notice)
    assert created.status_code==201, created.json
    stranger=auth_client(app,tenant_user)
    assert stranger.get("/api/v1/leases/"+lease.id+"/notices").status_code==200
    assert cli.post("/api/v1/leases/"+lease.id+"/renew",headers=csrf(cli),json={
        **rent,"new_rent_ugx":180000,"rent_notice_id":created.json["notice"]["id"]}).status_code==409
    renewed=cli.post("/api/v1/leases/"+lease.id+"/renew",headers=csrf(cli),json={
        **rent,"rent_notice_id":created.json["notice"]["id"]})
    assert renewed.status_code==201,renewed.json

def test_vacancy_metrics_and_tenant_credit_balance(app):
    owner,user,room,tenant,prop=fixture_records(app)
    for status in ("OCCUPIED","MAINTENANCE","RESERVED","ARCHIVED"):
        db.session.add(Room(property_id=prop.id,number=status,rent_ugx=150000,status=status))
    db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=tenant.id,start_date=date(2026,1,1),
                end_date=date(2027,12,31),rent_ugx=150000,deposit_ugx=150000)
    db.session.add(lease);db.session.flush()
    db.session.add_all([
        Invoice(lease_id=lease.id,tenant_id=tenant.id,invoice_number="KATS-BAL-1",
                period_start=date(2026,7,1),period_end=date(2026,7,31),
                due_date=date(2026,7,5),total_ugx=150000,paid_ugx=25000,
                credit_ugx=20000,status="PARTIALLY_PAID"),
        Invoice(lease_id=lease.id,tenant_id=tenant.id,invoice_number="KATS-BAL-2",
                period_start=date(2026,8,1),period_end=date(2026,8,31),
                due_date=date(2026,8,5),total_ugx=150000,status="VOID"),
    ]);db.session.commit()
    dash=auth_client(app,owner).get("/api/v1/dashboard")
    assert dash.status_code==200
    assert dash.json["vacant_rooms"]==1
    assert dash.json["reserved_rooms"]==1
    assert dash.json["unavailable_rooms"]==1
    out=auth_client(app,user).get("/api/v1/tenant/dashboard")
    assert out.status_code==200
    assert out.json["outstanding_ugx"]==105000
    assert out.json["credited_ugx"]==20000 and out.json["invoices"]==1

def test_nonoverlap_of_manual_rent_invoices(app):
    owner,_,room,tenant,_=fixture_records(app)
    room.status="OCCUPIED"
    lease=Lease(room_id=room.id,tenant_id=tenant.id,start_date=date(2026,1,1),
                end_date=date(2027,12,31),rent_ugx=150000,deposit_ugx=150000)
    db.session.add(lease);db.session.commit()
    cli=auth_client(app,owner)
    original={"lease_id":lease.id,"period_start":"2026-11-01","period_end":"2026-11-20",
              "due_date":"2026-11-05","total_ugx":100000}
    assert cli.post("/api/v1/invoices",headers=csrf(cli),json=original).status_code==201
    assert cli.post("/api/v1/invoices",headers=csrf(cli),json={
        **original,"period_start":"2026-11-10","period_end":"2026-11-30"}).status_code==409
    assert cli.post("/api/v1/invoices",headers=csrf(cli),json={
        **original,"period_start":"2026-11-21","period_end":"2026-11-30"}).status_code==201
