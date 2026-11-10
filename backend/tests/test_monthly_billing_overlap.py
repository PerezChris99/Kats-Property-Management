from datetime import date
from app.billing import generate_monthly_rent
from app.extensions import db
from app.models import Property,Room,Tenant,Lease,Invoice,InvoiceLine
from conftest import create_user

def test_monthly_scheduler_does_not_double_bill_manual_partial_rent(app):
    actor=create_user("monthly-overlap-actor@kats.test","OWNER")
    p=Property(name="Rent block",address="Kampala",district="Kampala")
    db.session.add(p);db.session.flush()
    room=Room(property_id=p.id,number="U1",status="OCCUPIED",rent_ugx=200000,deposit_ugx=200000)
    tenant=Tenant(full_name="Occupant",phone="+256700000001")
    db.session.add_all([room,tenant]);db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=tenant.id,
        start_date=date(2026,1,1),end_date=date(2027,12,31),
        rent_ugx=200000,deposit_ugx=200000)
    db.session.add(lease);db.session.flush()
    inv=Invoice(lease_id=lease.id,tenant_id=tenant.id,invoice_number="KATS-MANUAL-OCT",
                period_start=date(2026,11,10),period_end=date(2026,11,30),
                due_date=date(2026,11,15),total_ugx=140000,status="ISSUED")
    db.session.add(inv);db.session.flush()
    db.session.add(InvoiceLine(invoice_id=inv.id,charge_type="RENT",
        description="Approved partial rent",quantity=1,unit_price_ugx=140000,
        amount_ugx=140000))
    db.session.commit()
    result=generate_monthly_rent(date(2026,11,1),actor)
    assert result["issued"]==0
    assert result["requires_manual_proration_review"]==1
    assert db.session.query(Invoice).count()==1
