"""Seed synthetic rental accounts in a disposable E2E database ONLY."""
import os
from datetime import date
from urllib.parse import urlsplit
from argon2 import PasswordHasher
from app import create_app
from app.extensions import db
from app.models import (User, Property, Room, Tenant, Lease, Invoice,
                        InvoiceLine, LedgerEntry, CaretakerAssignment, MaintenanceRequest)

url = os.getenv("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://", 1)
parsed = urlsplit(url)
if (os.getenv("APP_ENV") != "testing" or os.getenv("KATS_TEST_MODE") != "1"
        or parsed.hostname != "db" or parsed.path != "/kats_e2e"
        or parsed.username != "kats_e2e"):
    raise SystemExit("REFUSED: seed_e2e may run ONLY on isolated db/kats_e2e")
password = os.getenv("KATS_E2E_PASSWORD", "")
if len(password) < 32:
    raise SystemExit("An ephemeral strong KATS_E2E_PASSWORD is required")
app = create_app()
roles = ("OWNER", "SUPER_ADMIN", "MANAGER", "ACCOUNTANT", "CARETAKER", "TENANT")
with app.app_context():
    if db.session.query(User.id).filter(User.email.like("%@e2e.kats.test")).first():
        raise SystemExit("E2E accounts already exist; rebuild the disposable stack")
    hasher = PasswordHasher()
    accounts = {}
    for role in roles:
        user = User(full_name="E2E " + role.replace("_", " ").title(),
                    email=role.lower() + "@e2e.kats.test",
                    password_hash=hasher.hash(password), role=role)
        db.session.add(user)
        accounts[role] = user
    db.session.flush()
    property_ = Property(name="E2E Synthetic Apartments", address="Local Test Only",
                         district="Kampala")
    db.session.add(property_)
    db.session.flush()
    room = Room(property_id=property_.id, number="E2E-01", rent_ugx=300000,
                deposit_ugx=0, status="OCCUPIED")
    tenant = Tenant(full_name="E2E Tenant", phone="+256700000999",
                    email="tenant@e2e.kats.test", user_id=accounts["TENANT"].id)
    db.session.add_all([room, tenant])
    db.session.flush()
    lease = Lease(tenant_id=tenant.id, room_id=room.id,
                  start_date=date(2026, 1, 1), end_date=date(2028, 12, 31),
                  rent_ugx=300000, deposit_ugx=0)
    db.session.add(lease)
    db.session.flush()
    invoice = Invoice(invoice_number="KATS-E2E-SYNTHETIC-001", lease_id=lease.id,
                      tenant_id=tenant.id, period_start=date(2026, 11, 1),
                      period_end=date(2026, 11, 30), due_date=date(2026, 11, 5),
                      total_ugx=300000)
    db.session.add(invoice)
    db.session.flush()
    db.session.add_all([
        InvoiceLine(invoice_id=invoice.id, description="Synthetic test rent",
                    charge_type="RENT", quantity=1,
                    unit_price_ugx=300000, amount_ugx=300000),
        LedgerEntry(invoice_id=invoice.id, event="INVOICE_ISSUED", amount_ugx=300000),
        CaretakerAssignment(room_id=room.id, caretaker_user_id=accounts["CARETAKER"].id),
        MaintenanceRequest(room_id=room.id, tenant_id=tenant.id,
                           title="E2E sample tap check", description="Synthetic test record",
                           priority="LOW"),
    ])
    db.session.commit()
print("Six synthetic roles and a sample lease/invoice/work order seeded in kats_e2e only.")
