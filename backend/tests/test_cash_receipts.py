from datetime import date
from app.extensions import db
from app.models import Property,Room,Tenant,Lease,Invoice,Payment
from conftest import create_user,auth_client

def test_in_person_cash_receipt_is_available_before_reconciliation_but_not_public(app):
    cashier=create_user("cash-custody@kats.test","OWNER")
    tenant_user=create_user("cash-client@kats.test","TENANT")
    other=create_user("cash-outsider@kats.test","TENANT")
    prop=Property(name="Kats Court",address="Kampala",district="Kampala")
    db.session.add(prop);db.session.flush()
    room=Room(property_id=prop.id,number="C1",rent_ugx=200000,status="OCCUPIED")
    tenant=Tenant(full_name="Person paying cash",phone="+256700009990",user_id=tenant_user.id)
    db.session.add_all([room,tenant]);db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=tenant.id,start_date=date(2026,1,1),
                end_date=date(2027,12,31),rent_ugx=200000,deposit_ugx=200000)
    db.session.add(lease);db.session.flush()
    invoice=Invoice(invoice_number="KATS-CASH-TEST",lease_id=lease.id,tenant_id=tenant.id,
        period_start=date(2026,11,1),period_end=date(2026,11,30),
        due_date=date(2026,11,5),total_ugx=200000,status="ISSUED")
    db.session.add(invoice);db.session.flush()
    payment=Payment(invoice_id=invoice.id,amount_ugx=100000,method="CASH",
       status="PENDING_REVIEW",created_by=cashier.id,idempotency_key="cash-custody-test")
    db.session.add(payment);db.session.commit()
    path="/api/v1/payments/"+payment.id+"/cash-acknowledgement.pdf"
    assert app.test_client().get(path).status_code==401
    assert auth_client(app,other).get(path).status_code==404
    response=auth_client(app,tenant_user).get(path)
    assert response.status_code==200
    assert response.data.startswith(b"%PDF")
    assert response.headers["Cache-Control"]=="no-store"
    assert auth_client(app,cashier).get(path).status_code==200
