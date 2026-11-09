from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, LeaseAmendment, DepositMovement, Inspection
from app.billing import generate_monthly_rent
from conftest import create_user, auth_client, csrf

def test_lease_renewal_preserves_billing_history(app):
    owner=create_user("renew-owner@kats.test","OWNER")
    prop=Property(name="West Court",address="Kampala",district="Kampala")
    db.session.add(prop);db.session.flush()
    room=Room(property_id=prop.id,number="R-1",status="OCCUPIED",rent_ugx=150000,deposit_ugx=150000)
    tenant=Tenant(full_name="Tenant",phone="+256700040000")
    db.session.add_all([room,tenant]);db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=tenant.id,
                start_date=date(2026,1,1),end_date=date(2026,12,31),
                rent_ugx=150000,deposit_ugx=150000)
    db.session.add(lease);db.session.commit()
    first=generate_monthly_rent(date(2026,12,1),owner)
    assert first["issued"]==1
    owner_client=auth_client(app,owner)
    renewed=owner_client.post("/api/v1/leases/"+lease.id+"/renew",headers=csrf(owner_client),
        json={"new_end_date":"2028-12-31","new_rent_ugx":180000,
              "reason":"Tenant signed annual renewal"})
    assert renewed.status_code==201,renewed.json
    assert renewed.json["amendment"]["effective_date"]=="2027-01-01"
    after=generate_monthly_rent(date(2027,2,1),owner)
    assert after["issued"]==1
    billed=db.session.query(Invoice).order_by(Invoice.period_start).all()
    assert [i.total_ugx for i in billed]==[150000,180000]
    assert db.session.query(LeaseAmendment).count()==1
    assert db.session.get(Lease,lease.id).rent_ugx==150000

def test_deposit_hold_withhold_and_refund_require_verified_two_person_review(app):
    maker=create_user("deposit-maker@kats.test","OWNER")
    checker=create_user("deposit-review@kats.test","ACCOUNTANT")
    prop=Property(name="Secure Rent",address="Kampala",district="Kampala")
    db.session.add(prop);db.session.flush()
    room=Room(property_id=prop.id,number="D-1",status="OCCUPIED",rent_ugx=150000,deposit_ugx=150000)
    tenant=Tenant(full_name="Deposit tenant",phone="+256700050000")
    db.session.add_all([room,tenant]);db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=tenant.id,
                start_date=date(2026,1,1),end_date=date(2027,12,31),
                rent_ugx=150000,deposit_ugx=150000)
    db.session.add(lease);db.session.commit()
    owner=auth_client(app,maker)
    accountant=auth_client(app,checker)
    hold=owner.post("/api/v1/deposits/movements",headers=csrf(owner),json={
        "lease_id":lease.id,"kind":"HOLD","amount_ugx":150000,
        "reason":"Verified deposit receipt","external_reference":"cash-receipt-1","idempotency_key":"hold-unique-1"
    })
    assert hold.status_code==201,hold.json
    movement_id=hold.json["movement"]["id"]
    blocked=owner.post("/api/v1/deposits/movements/"+movement_id+"/review",headers=csrf(owner),
        json={"decision":"APPROVE","reason":"Cannot self approve"})
    assert blocked.status_code==403
    confirm=accountant.post("/api/v1/deposits/movements/"+movement_id+"/review",
        headers=csrf(accountant),json={"decision":"APPROVE","reason":"Verified receipt"})
    assert confirm.status_code==200,confirm.json
    assert confirm.json["balance"]["available_ugx"]==150000
    premature=owner.post("/api/v1/deposits/movements",headers=csrf(owner),json={
        "lease_id":lease.id,"kind":"REFUND","amount_ugx":130000,"reason":"Returned deposit",
        "external_reference":"bank-refund-1","idempotency_key":"refund-1"
    })
    assert premature.status_code==409
    inspected=owner.post("/api/v1/inspections",headers=csrf(owner),json={
        "lease_id":lease.id,"kind":"MOVE_OUT","observed_on":"2026-11-09",
        "condition_notes":"Furniture and paint inspected","damage_estimate_ugx":20000
    })
    assert inspected.status_code==201
    assert owner.post("/api/v1/leases/"+lease.id+"/terminate",headers=csrf(owner),
        json={"reason":"Moved out"}).status_code==200
    withheld=owner.post("/api/v1/deposits/movements",headers=csrf(owner),json={
        "lease_id":lease.id,"kind":"WITHHOLD","amount_ugx":20000,
        "reason":"Paint damage","idempotency_key":"damage-1"})
    assert withheld.status_code==201,withheld.json
    approved=accountant.post("/api/v1/deposits/movements/"+withheld.json["movement"]["id"]+"/review",
        headers=csrf(accountant),json={"decision":"APPROVE","reason":"Damage inspected"})
    assert approved.status_code==200
    assert approved.json["balance"]["available_ugx"]==130000
    returned=owner.post("/api/v1/deposits/movements",headers=csrf(owner),json={
        "lease_id":lease.id,"kind":"REFUND","amount_ugx":130000,
        "reason":"Bank return","external_reference":"bank-refund-1","idempotency_key":"refund-1"})
    assert returned.status_code==201,returned.json
    approved_refund=accountant.post("/api/v1/deposits/movements/"+returned.json["movement"]["id"]+"/review",
        headers=csrf(accountant),json={"decision":"APPROVE","reason":"Checked bank transfer"})
    assert approved_refund.status_code==200,approved_refund.json
    assert approved_refund.json["balance"]["available_ugx"]==0
    assert db.session.query(DepositMovement).filter_by(status="APPROVED").count()==3
