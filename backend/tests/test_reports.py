from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, Expense
from conftest import create_user, auth_client

def test_ugx_reporting_scope_and_csv_export(app):
    owner = create_user("reports-owner@kats.test", "OWNER")
    tenant_user = create_user("reports-tenant@kats.test", "TENANT")
    prop = Property(name="West", address="Wakiso", district="Wakiso")
    db.session.add(prop)
    db.session.flush()
    room = Room(property_id=prop.id, number="101", rent_ugx=200000, status="OCCUPIED")
    occupant = Tenant(full_name="Tenant", phone="+256700000099")
    db.session.add_all([room, occupant])
    db.session.flush()
    lease = Lease(room_id=room.id, tenant_id=occupant.id, start_date=date(2026, 1, 1),
                  end_date=date(2027, 1, 1), rent_ugx=200000)
    db.session.add(lease)
    db.session.flush()
    invoice = Invoice(invoice_number="KATS-REPORT-TEST", lease_id=lease.id, tenant_id=occupant.id,
                      period_start=date(2026, 11, 1), period_end=date(2026, 11, 30),
                      due_date=date(2026, 11, 5), total_ugx=200000, paid_ugx=120000,
                      status="PARTIALLY_PAID")
    expense = Expense(property_id=prop.id, category="Repairs", description="Tap replacement",
                      amount_ugx=30000, incurred_on=date(2026, 11, 8), created_by=owner.id,
                      status="APPROVED")
    db.session.add_all([invoice, expense])
    db.session.commit()
    cli = auth_client(app, owner)
    summary = cli.get("/api/v1/reports/summary?month=2026-11")
    assert summary.status_code == 200, summary.json
    assert summary.json["billed_ugx"] == 200000
    assert summary.json["applied_to_invoices_ugx"] == 120000
    assert summary.json["outstanding_on_invoices_ugx"] == 80000
    assert summary.json["expenses_in_period_ugx"] == 30000
    assert summary.json["occupancy_percent"] == 100
    assert cli.get("/api/v1/reports/summary?month=wrong").status_code == 400
    exported = cli.get("/api/v1/reports/export/invoices.csv")
    assert exported.status_code == 200
    assert b"KATS-REPORT-TEST" in exported.data
    outsider = auth_client(app, tenant_user)
    assert outsider.get("/api/v1/reports/summary").status_code == 403
    assert outsider.get("/api/v1/reports/arrears").status_code == 403
    assert outsider.get("/api/v1/reports/export/invoices.csv").status_code == 403
