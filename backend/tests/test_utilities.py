from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, CaretakerAssignment, InvoiceLine
from app.utility_models import UtilityMeter, UtilityReading
from conftest import create_user, auth_client, csrf

def setup_accounts(app):
    owner=create_user("meter-owner@kats.test","OWNER")
    accountant=create_user("meter-accountant@kats.test","ACCOUNTANT")
    caretaker=create_user("meter-caretaker@kats.test","CARETAKER")
    tenant_user=create_user("meter-tenant@kats.test","TENANT")
    prop=Property(name="Apartment Block",address="Kampala",district="Kampala")
    db.session.add(prop);db.session.flush()
    room=Room(property_id=prop.id,number="B1",status="OCCUPIED",rent_ugx=150000,deposit_ugx=150000)
    tenant=Tenant(full_name="Occupant",phone="256700000002",user_id=tenant_user.id)
    db.session.add_all([room,tenant]);db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=tenant.id,start_date=date(2026,1,1),
                end_date=date(2027,12,31),rent_ugx=150000,deposit_ugx=150000)
    db.session.add(lease)
    db.session.add(CaretakerAssignment(room_id=room.id,caretaker_user_id=caretaker.id))
    db.session.flush()
    invoice=Invoice(lease_id=lease.id,tenant_id=tenant.id,invoice_number="KATS-UTILITY-1",
                    period_start=date(2026,11,1),period_end=date(2026,11,30),
                    due_date=date(2026,11,5),total_ugx=150000,status="ISSUED")
    db.session.add(invoice);db.session.commit()
    return owner,accountant,caretaker,tenant_user,room,invoice

def test_utility_meter_reading_billing_is_audited_approved_and_not_duplicated(app):
    owner,accountant,caretaker,tenant_user,room,invoice=setup_accounts(app)
    admin=auth_client(app,owner)
    created=admin.post("/api/v1/utilities/meters",headers=csrf(admin),
        json={"room_id":room.id,"kind":"WATER","tariff_ugx_per_unit":6000,
              "baseline_milli_units":10000})
    assert created.status_code==201,created.json
    meter_id=created.json["meter"]["id"]
    worker=auth_client(app,caretaker)
    cmd={"observed_on":"2026-11-09","current_milli_units":12500,"idempotency_key":"water-meter-nov"}
    reading=worker.post("/api/v1/utilities/meters/"+meter_id+"/readings",
        headers=csrf(worker),json=cmd)
    assert reading.status_code==201,reading.json
    assert reading.json["reading"]["charge_ugx"]==15000
    again=worker.post("/api/v1/utilities/meters/"+meter_id+"/readings",headers=csrf(worker),json=cmd)
    assert again.status_code==200 and again.json["reused"]
    reading_id=reading.json["reading"]["id"]
    assert admin.post("/api/v1/utilities/readings/"+reading_id+"/apply",
        headers=csrf(admin),json={"invoice_id":invoice.id}).status_code==200
    reviewer=auth_client(app,accountant)
    assert reviewer.post("/api/v1/utilities/readings/"+reading_id+"/apply",
        headers=csrf(reviewer),json={"invoice_id":invoice.id}).status_code==409
    assert db.session.get(Invoice,invoice.id).total_ugx==165000
    assert db.session.query(InvoiceLine).filter_by(charge_type="WATER").count()==1
    tenant=auth_client(app,tenant_user)
    assert len(tenant.get("/api/v1/utilities/meters").json["items"])==1

def test_unassigned_caretaker_cannot_access_readings_and_meters_must_increase(app):
    owner,accountant,caretaker,tenant_user,room,invoice=setup_accounts(app)
    admin=auth_client(app,owner)
    meter=admin.post("/api/v1/utilities/meters",headers=csrf(admin),
        json={"room_id":room.id,"kind":"ELECTRICITY","tariff_ugx_per_unit":800,
              "baseline_milli_units":30000})
    assert meter.status_code==201
    meter_id=meter.json["meter"]["id"]
    caretaker_cli=auth_client(app,caretaker)
    invalid=caretaker_cli.post("/api/v1/utilities/meters/"+meter_id+"/readings",
        headers=csrf(caretaker_cli),json={"observed_on":"2026-11-09","current_milli_units":29000,
                          "idempotency_key":"regression-1"})
    assert invalid.status_code==409
    unassigned=create_user("meter-unassigned@kats.test","CARETAKER")
    outsider=auth_client(app,unassigned)
    assert outsider.get("/api/v1/utilities/meters/"+meter_id+"/readings").status_code==404
