"""Seed a realistic but entirely synthetic 31-account KATS LOCAL preview.

This command only writes to the ignored .local/kats-preview.sqlite3 after the
same strict environment checks as ops/init_preview.py. It is idempotent and
never imports real contact data or touches a deployed database.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from contextlib import nullcontext
from urllib.parse import urlparse
from secrets import token_urlsafe
from sys import path as sys_path

from argon2 import PasswordHasher

ROOT = Path(__file__).resolve().parents[1]
BACK = ROOT / "backend"
if str(BACK) not in sys_path:
    sys_path.insert(0, str(BACK))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    User, Property, Building, Floor, Room, Tenant, Lease, Invoice, InvoiceLine,
    LedgerEntry, Payment, RoomStateHistory, MaintenanceRequest, AuditLog,
)
from app.demo_preview import assert_preview_database  # noqa: E402

NAMES = (
    "Sarah Namusoke", "Brian Ssemakula", "Esther Nakato", "Isaac Mugisha",
    "Ruth Nanyonjo", "Daniel Kato", "Mariam Nankya", "Paul Ssewankambo",
    "Grace Achieng", "Peter Waiswa", "Rose Atim", "Michael Kizza",
    "Annet Nambasa", "Joseph Muwanga", "Patience Akello", "David Tumusiime",
    "Sharon Nabuuma", "Samuel Otema", "Mercy Nakyeyune", "Andrew Kaggwa",
    "Irene Nabukenya", "Richard Okello", "Juliet Namutebi", "Robert Mukasa",
    "Joan Asiimwe", "Denis Walusimbi", "Faith Nabirye", "Martin Lule",
    "Brenda Nsubuga", "Patrick Odongo",
)
PROPERTIES = (
    ("Crestview Apartments (Demo)", "Ntinda, Kampala — synthetic portfolio", "Kampala", 12),
    ("Lakeside Court (Demo)", "Entebbe Road, Wakiso — synthetic portfolio", "Wakiso", 11),
    ("Garden Flats (Demo)", "Kira, Wakiso — synthetic portfolio", "Wakiso", 10),
)
DOMAIN = "demo.kats.invalid"
LANDLORD_EMAIL = "landlord@" + DOMAIN


def demo_email(n: int) -> str:
    return f"tenant{n:02d}@{DOMAIN}"


def verify_existing():
    """Re-running never resets passwords, edits tenant data or creates duplicates."""
    email_list = [LANDLORD_EMAIL, *[demo_email(i) for i in range(1, 31)]]
    users = db.session.query(User).filter(User.email.in_(email_list)).all()
    if not users:
        return False
    if len(users) != 31:
        raise RuntimeError("Partial demo accounts found. Refusing automatic changes.")
    landlord = next((u for u in users if u.email == LANDLORD_EMAIL and u.role == "OWNER"), None)
    if landlord is None:
        raise RuntimeError("Existing demo landlord has wrong role. Refusing changes.")
    for i in range(1, 31):
        user = next((u for u in users if u.email == demo_email(i) and u.role == "TENANT"), None)
        if user is None:
            raise RuntimeError("Demo tenant account missing or role changed.")
        tenant = db.session.query(Tenant).filter_by(user_id=user.id).first()
        if not tenant or not db.session.query(Lease.id).filter_by(tenant_id=tenant.id, status="ACTIVE").first():
            raise RuntimeError("Demo tenancy data incomplete. Refusing changes.")
        if db.session.query(Invoice.id).filter_by(tenant_id=tenant.id).count() < 2:
            raise RuntimeError("Demo rent records incomplete. Refusing changes.")
    return True


def previous_month(d: date) -> date:
    return (d.replace(day=1) - timedelta(days=1)).replace(day=1)


def month_end(d: date) -> date:
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def assert_public_neon_demo_database():
    """A deliberately explicit, one-off seed against a dedicated empty Neon DB.

    Seeding operates in staging context; production runtime must use a
    separately provisioned non-owner, non-BYPASSRLS database role.
    """
    if os.getenv("KATS_PUBLIC_DEMO_SEED") != "1" or os.getenv("APP_ENV") != "staging":
        raise RuntimeError("External synthetic dataset requires staging context and explicit KATS_PUBLIC_DEMO_SEED=1")
    parsed = urlparse(os.getenv("DATABASE_URL", ""))
    if (parsed.scheme not in ("postgresql", "postgresql+psycopg") or
        not parsed.hostname or not parsed.hostname.endswith(".neon.tech") or
        parsed.path != "/katsproperty" or not parsed.username or
        not parsed.password):
        raise RuntimeError("Refusing to seed any database other than the dedicated katsproperty Neon PostgreSQL database")
    password = os.getenv("KATS_PUBLIC_DEMO_PASSWORD", "")
    if (len(password) < 16 or password.startswith("REPLACE") or
        password.startswith("development")):
        raise RuntimeError("A distinct 16+ character public demonstration password is required")
    for provider in ("MTN_MOMO_ENABLED", "AIRTEL_MONEY_ENABLED", "EFRIS_ENABLED"):
        if os.getenv(provider, "false").lower() == "true":
            raise RuntimeError("Public synthetic demo cannot enable live payment/fiscal providers")


def seed(public_demo=False) -> None:
    if public_demo:
        assert_public_neon_demo_database()
    else:
        assert_preview_database()
    app = create_app()
    from app.document_rls import trusted_worker_scope
    with app.app_context(), (trusted_worker_scope() if public_demo else nullcontext()):
        if public_demo:
            assert_public_neon_demo_database()
            # Never modify a non-empty customer database through a demo
            # setup script. A previous complete demo remains idempotent.
            from sqlalchemy import inspect
            if not inspect(db.engine).has_table("users"):
                raise RuntimeError("Schema migrations must be completed before demonstration seeding")
            occupied = db.session.query(User.id).filter(
                ~User.email.like("%@demo.kats.invalid")).first()
            if occupied:
                raise RuntimeError("Refusing seed: non-demo user already exists")
        else:
            assert_preview_database(app)
        if verify_existing():
            print("[DEMO] Existing landlord and 30 linked tenants verified; no changes.", flush=True)
            return
        # Realistic fiction, not real people, telephone numbers, addresses or payments.
        hasher = PasswordHasher()
        preview_password_hash = hasher.hash(
            os.environ["KATS_PUBLIC_DEMO_PASSWORD"] if public_demo else token_urlsafe(32)
        )
        landlord = User(full_name="Grace Namatovu (Demo Landlord)",
                        email=LANDLORD_EMAIL,
                        password_hash=preview_password_hash, role="OWNER")
        db.session.add(landlord)
        db.session.flush()
        # Use the current Kampala calendar so the rent figures make sense on launch.
        today = datetime.now(timezone(timedelta(hours=3))).date()
        invoice_months = (previous_month(today), today.replace(day=1))
        property_rooms = []
        for name, address, district, count in PROPERTIES:
            prop = Property(name=name, address=address, district=district)
            db.session.add(prop)
            db.session.flush()
            building = Building(property_id=prop.id, name="Main Block", description="Fictional demo building")
            db.session.add(building)
            db.session.flush()
            floors = []
            for level, label in enumerate(("Ground", "First", "Second")):
                floor = Floor(building_id=building.id, level=level, label=label + " Floor")
                db.session.add(floor)
                db.session.flush()
                floors.append(floor)
            for j in range(count):
                rent = 320_000 + (len(property_rooms) % 12) * 65_000
                room = Room(property_id=prop.id, floor_id=floors[j % 3].id,
                            number=f"{j % 3 + 1}{j // 3 + 1:02d}",
                            status="VACANT", rent_ugx=rent, deposit_ugx=rent)
                db.session.add(room)
                property_rooms.append(room)
        db.session.flush()
        # Exactly 30 occupied rooms and three vacant demonstration units.
        for i, (name, room) in enumerate(zip(NAMES, property_rooms), start=1):
            user = User(full_name=name, email=demo_email(i),
                        password_hash=preview_password_hash, role="TENANT")
            db.session.add(user)
            db.session.flush()
            tenant = Tenant(user_id=user.id, full_name=name,
                            phone=f"0700 000 {i:03d}", email=user.email)
            db.session.add(tenant)
            db.session.flush()
            start = today - timedelta(days=180 + (i % 6) * 30)
            end = today + timedelta(days=365 + (i % 5) * 30)
            lease = Lease(tenant_id=tenant.id, room_id=room.id, start_date=start,
                          end_date=end, rent_ugx=room.rent_ugx,
                          deposit_ugx=room.rent_ugx, due_day=5, status="ACTIVE")
            db.session.add(lease)
            room.status = "OCCUPIED"
            db.session.flush()
            db.session.add(RoomStateHistory(
                room_id=room.id, old_status="VACANT", new_status="OCCUPIED",
                reason="Synthetic demo lease", actor_id=landlord.id,
            ))
            for month in invoice_months:
                # Older and current invoices give the demo tenant meaningful history.
                paid = (room.rent_ugx if (i + month.month) % 5 < 3 else
                        room.rent_ugx // 2 if (i + month.month) % 5 == 3 else 0)
                invoice = Invoice(
                    invoice_number=f"DEMO-{i:02d}-{month:%Y%m}",
                    lease_id=lease.id, tenant_id=tenant.id,
                    period_start=month, period_end=month_end(month),
                    due_date=month.replace(day=5), total_ugx=room.rent_ugx,
                    paid_ugx=paid,
                    status="PAID" if paid == room.rent_ugx else
                           "PARTIALLY_PAID" if paid else "ISSUED",
                )
                db.session.add(invoice)
                db.session.flush()
                db.session.add(InvoiceLine(
                    invoice_id=invoice.id, description="Monthly rent (synthetic)",
                    charge_type="RENT", quantity=1,
                    unit_price_ugx=room.rent_ugx, amount_ugx=room.rent_ugx,
                ))
                db.session.add(LedgerEntry(
                    invoice_id=invoice.id, event="INVOICE_ISSUED",
                    amount_ugx=room.rent_ugx,
                ))
                if paid:
                    payment = Payment(
                        invoice_id=invoice.id, amount_ugx=paid, method="BANK_TRANSFER",
                        status="RECONCILED", settled_at=datetime.now(timezone.utc),
                        reference=f"DEMO-RECON-{i:02d}-{month:%Y%m}",
                        idempotency_key=f"demo-reconciled-{i:02d}-{month:%Y%m}",
                        created_by=user.id, reviewed_by=landlord.id,
                    )
                    db.session.add(payment)
                    db.session.flush()
                    db.session.add(LedgerEntry(
                        invoice_id=invoice.id, payment_id=payment.id,
                        event="PAYMENT_RECEIVED", amount_ugx=paid,
                    ))
            if i % 7 == 0:
                db.session.add(MaintenanceRequest(
                    room_id=room.id, tenant_id=tenant.id,
                    title=("Leaking kitchen tap" if i % 2 else "Corridor lighting"),
                    description="Fictitious maintenance request for preview testing.",
                    priority="MEDIUM",
                ))
        db.session.add(AuditLog(
            actor_id=landlord.id, action="demo.seed", target_type="demo",
            target_id=landlord.id,
            details={"tenants": 30, "properties": 3, "rooms": 33, "synthetic": True},
        ))
        db.session.commit()
        print("[DEMO] Seeded 1 OWNER, 30 TENANT accounts, 3 properties, 33 rooms, "
              "30 linked leases, 60 invoices and realistic demo payments. "
              "Open /login and choose a demo account.", flush=True)


if __name__ == "__main__":
    seed()
