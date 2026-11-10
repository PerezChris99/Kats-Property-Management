"""Release-boundary checks: exact UGX accounting, CSRF and dangerous JSON shapes."""
from datetime import date
import pytest
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, InvoiceLine, LedgerEntry, Payment
from conftest import create_user, auth_client, csrf


def seeded_invoice_client(app):
    user = create_user("release-owner@kats.test", "OWNER")
    property_ = Property(name="Release Court", address="Kampala", district="Kampala")
    db.session.add(property_)
    db.session.flush()
    room = Room(property_id=property_.id, number="B1", rent_ugx=250000, status="OCCUPIED")
    tenant = Tenant(full_name="Contract Tenant", phone="+256700100500")
    db.session.add_all([room, tenant])
    db.session.flush()
    lease = Lease(room_id=room.id, tenant_id=tenant.id,
                  start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
                  rent_ugx=250000, deposit_ugx=0)
    db.session.add(lease)
    db.session.commit()
    return auth_client(app, user), lease


def invoice_body(lease, **overrides):
    return {
        "lease_id": lease.id,
        "period_start": "2026-11-01",
        "period_end": "2026-11-30",
        "due_date": "2026-11-05",
        **overrides,
    }


@pytest.mark.parametrize("invalid", [True, False, 100.25, "250000", -1, 10**16, None])
def test_invoice_ugx_cannot_be_boolean_float_string_negative_or_overflow(app, invalid):
    client, lease = seeded_invoice_client(app)
    result = client.post("/api/v1/invoices", headers=csrf(client),
                         json=invoice_body(lease, total_ugx=invalid))
    assert result.status_code == 400, result.json
    assert db.session.query(Invoice).count() == 0
    assert db.session.query(LedgerEntry).count() == 0


@pytest.mark.parametrize("bad_line", [
    {"charge_type": "RENT", "description": "Rent", "quantity": 0, "unit_price_ugx": 250000},
    {"charge_type": "RENT", "description": "Rent", "quantity": True, "unit_price_ugx": 250000},
    {"charge_type": "INVALID", "description": "Not a bill", "quantity": 1, "unit_price_ugx": 250000},
    {"charge_type": "RENT", "description": "Rent", "quantity": 1, "unit_price_ugx": "250000"},
    {"charge_type": "RENT", "description": "Rent", "quantity": 100001, "unit_price_ugx": 250000},
])
def test_malformed_invoice_lines_never_post_ledger(app, bad_line):
    client, lease = seeded_invoice_client(app)
    response = client.post("/api/v1/invoices", headers=csrf(client),
                           json=invoice_body(lease, lines=[bad_line]))
    assert response.status_code == 400, response.json
    assert db.session.query(Invoice).count() == 0
    assert db.session.query(LedgerEntry).count() == 0


def test_multi_line_invoice_posts_exact_integer_total_and_prevents_rent_overlap(app):
    client, lease = seeded_invoice_client(app)
    lines = [
        {"charge_type": "RENT", "description": "November rent", "quantity": 1, "unit_price_ugx": 250000},
        {"charge_type": "WATER", "description": "Reviewed water charge", "quantity": 2, "unit_price_ugx": 7500},
    ]
    response = client.post("/api/v1/invoices", headers=csrf(client),
                           json=invoice_body(lease, lines=lines, total_ugx=265000))
    assert response.status_code == 201, response.json
    invoice = db.session.query(Invoice).one()
    assert invoice.total_ugx == 265000
    assert sum(line.amount_ugx for line in db.session.query(InvoiceLine).all()) == 265000
    posted = db.session.query(LedgerEntry).filter_by(invoice_id=invoice.id, event="INVOICE_ISSUED").one()
    assert posted.amount_ugx == 265000
    duplicate = client.post("/api/v1/invoices", headers=csrf(client),
                            json=invoice_body(lease, total_ugx=250000))
    assert duplicate.status_code == 409, duplicate.json
    assert db.session.query(Invoice).count() == 1


def test_invoice_mismatched_calculated_line_total_is_rejected(app):
    client, lease = seeded_invoice_client(app)
    result = client.post("/api/v1/invoices", headers=csrf(client), json=invoice_body(
        lease, total_ugx=250001, lines=[
            {"charge_type": "RENT", "description": "Rent", "quantity": 1, "unit_price_ugx": 250000}
        ]
    ))
    assert result.status_code == 400
    assert db.session.query(Invoice).count() == 0


def test_explicit_csrf_required_even_for_owner_mutations(app):
    client, lease = seeded_invoice_client(app)
    response = client.post("/api/v1/invoices",
                           json=invoice_body(lease, total_ugx=250000))
    assert response.status_code in (401, 403)
    assert db.session.query(Invoice).count() == 0


def test_duplicate_cash_payment_key_cannot_change_invoice_or_amount(app):
    client, lease = seeded_invoice_client(app)
    created = client.post("/api/v1/invoices", headers=csrf(client),
                          json=invoice_body(lease, total_ugx=250000))
    assert created.status_code == 201
    payload = {"invoice_id": created.json["invoice"]["id"], "method": "CASH",
               "amount_ugx": 50000, "idempotency_key": "release-cash-1"}
    first = client.post("/api/v1/payments/manual", headers=csrf(client), json=payload)
    assert first.status_code == 201, first.json
    duplicate = client.post("/api/v1/payments/manual", headers=csrf(client),
                            json={**payload, "amount_ugx": 55000})
    assert duplicate.status_code == 409, duplicate.json
    assert db.session.query(Payment).count() == 1
    assert db.session.query(Invoice).one().paid_ugx == 0


def test_nested_json_resource_exhaustion_is_rejected_without_persistence(app):
    client = app.test_client()
    deep = {"value": "ok"}
    for _ in range(20):
        deep = {"child": deep}
    response = client.post("/api/v1/auth/login",
                           json={"email": "nobody@kats.test", "password": "abc", "payload": deep})
    assert response.status_code == 400
    assert db.session.query(Invoice).count() == 0


@pytest.mark.parametrize("path", [
    "/api/v1/properties", "/api/v1/invoices", "/api/v1/payments",
    "/api/v1/maintenance", "/api/v1/disputes", "/api/v1/privacy/requests",
    "/api/v1/maintenance/plans",
])
def test_sensitive_api_never_returns_cacheable_anonymous_data(app, path):
    result = app.test_client().get(path)
    assert result.status_code == 401, (path, result.status_code, result.json)
    assert result.headers.get("Cache-Control") == "no-store"
    assert result.headers.get("X-Content-Type-Options") == "nosniff"
