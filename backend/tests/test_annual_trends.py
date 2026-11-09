from datetime import date,datetime,timezone
from app.extensions import db
from app.models import Property,Room,Tenant,Lease,Invoice,Payment,Expense
from conftest import create_user,auth_client

def test_annual_trends_track_only_verified_dated_collections(app):
    owner=create_user("trend-owner@kats.test","OWNER")
    user=create_user("trend-tenant@kats.test","TENANT")
    prop=Property(name="Trends",address="Kampala",district="Kampala")
    db.session.add(prop);db.session.flush()
    room=Room(property_id=prop.id,number="T1",rent_ugx=250000,status="OCCUPIED")
    tenant=Tenant(full_name="Trends tenant",phone="+256700900000")
    db.session.add_all([room,tenant]);db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=tenant.id,
                start_date=date(2026,1,1),end_date=date(2027,1,1),rent_ugx=250000)
    db.session.add(lease);db.session.flush()
    invoice=Invoice(invoice_number="TREND-TEST",lease_id=lease.id,tenant_id=tenant.id,
       period_start=date(2026,11,1),period_end=date(2026,11,30),
       due_date=date(2026,11,9),total_ugx=250000,paid_ugx=150000,
       status="PARTIALLY_PAID")
    db.session.add(invoice);db.session.flush()
    events=[
        Payment(invoice_id=invoice.id,created_by=owner.id,idempotency_key="trend-paid",
           amount_ugx=100000,method="CASH",status="RECONCILED",
           settled_at=datetime(2026,11,9,12,tzinfo=timezone.utc)),
        Payment(invoice_id=invoice.id,created_by=owner.id,idempotency_key="trend-legacy",
           amount_ugx=50000,method="BANK_TRANSFER",status="RECONCILED",
           settled_at=None),
        Payment(invoice_id=invoice.id,created_by=owner.id,idempotency_key="trend-reversed",
           amount_ugx=40000,method="CASH",status="REVERSED",
           settled_at=datetime(2026,11,10,tzinfo=timezone.utc),
           reversed_at=datetime(2026,11,11,tzinfo=timezone.utc)),
    ]
    expense=Expense(property_id=prop.id,category="REPAIRS",description="Reviewed costs",
                    amount_ugx=20000,incurred_on=date(2026,11,8),
                    created_by=owner.id,status="APPROVED")
    db.session.add_all(events+[expense]);db.session.commit()
    cli=auth_client(app,owner)
    res=cli.get("/api/v1/reports/annual-trends?year=2026")
    assert res.status_code==200,res.json
    assert len(res.json["points"])==12
    nov=res.json["points"][10]
    assert nov["month"]=="2026-11"
    assert nov["verified_collections_ugx"]==100000
    assert nov["net_invoiced_ugx"]==250000
    assert nov["approved_expenses_incurred_ugx"]==20000
    assert res.json["legacy_verified_without_settlement_date_ugx"]==50000
    assert "not a cashflow" in res.json["methodology"].lower()
    assert cli.get("/api/v1/reports/annual-trends?year=invalid").status_code==400
    assert auth_client(app,user).get("/api/v1/reports/annual-trends?year=2026").status_code==403
