from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, LedgerEntry, AuditLog
from app.billing import generate_monthly_rent
from conftest import create_user

def test_monthly_billing_is_repeatable_and_audited(app):
    owner = create_user("billing-owner@kats.test", "OWNER")
    property = Property(name="Kats Heights", address="Kampala", district="Kampala")
    db.session.add(property)
    db.session.flush()
    room = Room(property_id=property.id, number="101", status="OCCUPIED", rent_ugx=350000, deposit_ugx=350000)
    tenant = Tenant(full_name="Sample tenant", phone="+256700000001")
    db.session.add_all([room, tenant])
    db.session.flush()
    lease = Lease(room_id=room.id, tenant_id=tenant.id, start_date=date(2026, 1, 1),
                  end_date=date(2027, 12, 31), rent_ugx=350000, deposit_ugx=350000,
                  due_day=5, status="ACTIVE")
    db.session.add(lease)
    db.session.commit()
    first = generate_monthly_rent(date(2026, 11, 24), owner)
    assert first == {"month": "2026-11-01", "issued": 1, "already_exists": 0, "requires_manual_proration_review": 0}
    second = generate_monthly_rent(date(2026, 11, 1), owner)
    assert second["issued"] == 0 and second["already_exists"] == 1
    invoice = db.session.query(Invoice).one()
    assert invoice.total_ugx == 350000 and invoice.paid_ugx == 0
    assert invoice.due_date == date(2026, 11, 5)
    assert db.session.query(LedgerEntry).count() == 1
    assert db.session.query(AuditLog).filter_by(action="billing.monthly_invoice_issued").count() == 1

def test_partial_month_is_not_silently_prorated(app):
    owner = create_user("another-owner@kats.test", "OWNER")
    prop = Property(name="Kats West", address="Kampala", district="Wakiso")
    db.session.add(prop)
    db.session.flush()
    room = Room(property_id=prop.id, number="205", status="OCCUPIED", rent_ugx=200000)
    tenant = Tenant(full_name="Second tenant", phone="+256700000002")
    db.session.add_all([room, tenant])
    db.session.flush()
    db.session.add(Lease(room_id=room.id, tenant_id=tenant.id, start_date=date(2026, 11, 15),
                        end_date=date(2027, 3, 31), rent_ugx=200000, due_day=15, status="ACTIVE"))
    db.session.commit()
    result = generate_monthly_rent(date(2026, 11, 1), owner)
    assert result["issued"] == 0
    assert result["requires_manual_proration_review"] == 1
    assert db.session.query(Invoice).count() == 0
