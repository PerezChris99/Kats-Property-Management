from datetime import date
from app.extensions import db
from app.models import Tenant, Invoice, LedgerEntry, AuditLog
from conftest import create_user, auth_client, csrf

def test_auth_and_role_isolation(app, client):
    assert client.get("/api/v1/properties").status_code == 401
    owner = create_user("owner@kats.test", "OWNER")
    tenant = create_user("tenant@kats.test", "TENANT")
    owned = auth_client(app, owner)
    response = owned.post("/api/v1/properties", headers=csrf(owned),
        json={"name": "Kats Court", "address": "Kampala", "district": "Kampala"})
    assert response.status_code == 201, response.json
    alien = auth_client(app, tenant)
    assert alien.get("/api/v1/properties").status_code == 403
    assert alien.get("/api/v1/audit").status_code == 403

def test_manual_payment_requires_separate_approval_and_is_idempotent(app):
    maker = create_user("maker@kats.test", "OWNER")
    checker = create_user("checker@kats.test", "ACCOUNTANT")
    writer = auth_client(app, maker)
    reviewer = auth_client(app, checker)
    headers = csrf(writer)
    prop_response = writer.post("/api/v1/properties", headers=headers,
        json={"name": "Property A", "address": "Kampala", "district": "Kampala"})
    assert prop_response.status_code == 201, prop_response.json
    prop_id = prop_response.json["property"]["id"]
    room_response = writer.post("/api/v1/rooms", headers=headers,
        json={"property_id": prop_id, "number": "A1", "rent_ugx": 250000})
    assert room_response.status_code == 201, room_response.json
    room_id = room_response.json["room"]["id"]
    tenant_response = writer.post("/api/v1/tenants", headers=headers,
        json={"full_name": "Tenant A", "phone": "+256700000000"})
    assert tenant_response.status_code == 201
    lease_response = writer.post("/api/v1/leases", headers=headers, json={
        "room_id": room_id, "tenant_id": tenant_response.json["tenant"]["id"],
        "start_date": "2026-11-01", "end_date": "2027-01-01", "rent_ugx": 250000
    })
    assert lease_response.status_code == 201, lease_response.json
    invoice_response = writer.post("/api/v1/invoices", headers=headers, json={
        "lease_id": lease_response.json["lease"]["id"],
        "period_start": "2026-11-01", "period_end": "2026-11-30",
        "due_date": "2026-11-05", "total_ugx": 250000
    })
    assert invoice_response.status_code == 201, invoice_response.json
    invoice_id = invoice_response.json["invoice"]["id"]
    pending_payload = {"invoice_id": invoice_id, "method": "CASH", "amount_ugx": 100000,
                       "idempotency_key": "pmt-0001"}
    pending = writer.post("/api/v1/payments/manual", json=pending_payload, headers=headers)
    assert pending.status_code == 201, pending.json
    payment_id = pending.json["payment"]["id"]
    repeated = writer.post("/api/v1/payments/manual", json=pending_payload, headers=headers)
    assert repeated.status_code == 200 and repeated.json["payment"]["id"] == payment_id
    assert db.session.get(Invoice, invoice_id).paid_ugx == 0
    assert writer.post("/api/v1/payments/" + payment_id + "/approve", headers=headers).status_code == 403
    confirmed = reviewer.post("/api/v1/payments/" + payment_id + "/approve", headers=csrf(reviewer))
    assert confirmed.status_code == 200, confirmed.json
    assert confirmed.json["invoice"]["paid_ugx"] == 100000
    assert reviewer.post("/api/v1/payments/" + payment_id + "/approve",
                         headers=csrf(reviewer)).status_code == 200
    assert db.session.query(LedgerEntry).filter_by(payment_id=payment_id).count() == 1
    reversed_payment = reviewer.post("/api/v1/payments/" + payment_id + "/reverse",
        headers=csrf(reviewer), json={"reason":"Duplicate cash collection found during reconciliation"})
    assert reversed_payment.status_code == 200, reversed_payment.json
    assert reversed_payment.json["invoice"]["paid_ugx"] == 0
    assert db.session.query(LedgerEntry).filter_by(payment_id=payment_id).count() == 2
    again_reversed = reviewer.post("/api/v1/payments/" + payment_id + "/reverse",
        headers=csrf(reviewer), json={"reason":"Repeated command"})
    assert again_reversed.status_code == 200
    assert db.session.query(LedgerEntry).filter_by(payment_id=payment_id).count() == 2
    voided = reviewer.post("/api/v1/invoices/" + invoice_id + "/void",
        headers=csrf(reviewer), json={"reason":"Invoice issued in error"})
    assert voided.status_code == 200, voided.json
    assert db.session.query(LedgerEntry).filter_by(invoice_id=invoice_id).count() == 4
    assert db.session.query(AuditLog).count() >= 7

def test_tenant_cannot_read_unlinked_data(app):
    user = create_user("tenant2@kats.test", "TENANT")
    db.session.add(Tenant(user_id=user.id, full_name="Tenant 2", phone="+256711111111"))
    db.session.commit()
    client = auth_client(app, user)
    invoices = client.get("/api/v1/invoices")
    assert invoices.status_code == 200
    assert invoices.json["total"] == 0
    assert client.get("/api/v1/dashboard").status_code == 403
