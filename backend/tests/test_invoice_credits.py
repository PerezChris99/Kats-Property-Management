from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, InvoiceLine, CreditNote, LedgerEntry
from conftest import create_user, auth_client, csrf

def seed():
    prop = Property(name="Credits", address="Kampala", district="Kampala")
    db.session.add(prop)
    db.session.flush()
    room = Room(property_id=prop.id, number="3", rent_ugx=160000, status="OCCUPIED")
    tenant = Tenant(full_name="Credit tenant", phone="+256780111111")
    db.session.add_all([room, tenant])
    db.session.flush()
    lease = Lease(room_id=room.id, tenant_id=tenant.id, start_date=date(2026, 1, 1),
                  end_date=date(2027, 1, 1), rent_ugx=160000)
    db.session.add(lease)
    db.session.commit()
    return lease.id

def test_invoice_lines_credits_and_balance(app):
    owner = create_user("creditowner@kats.test", "OWNER")
    maker = auth_client(app, owner)
    lease_id = seed()
    inv_res = maker.post("/api/v1/invoices", headers=csrf(maker), json={
        "lease_id":lease_id, "period_start":"2026-11-01", "period_end":"2026-11-30",
        "due_date":"2026-11-05", "lines":[
            {"description":"Rent","charge_type":"RENT","quantity":1,"unit_price_ugx":160000},
            {"description":"Water","charge_type":"WATER","quantity":2,"unit_price_ugx":10000}
        ]})
    assert inv_res.status_code == 201, inv_res.json
    invoice_id = inv_res.json["invoice"]["id"]
    assert inv_res.json["invoice"]["total_ugx"] == 180000
    detail = maker.get("/api/v1/invoices/"+invoice_id+"/lines")
    assert detail.status_code == 200 and len(detail.json["items"]) == 2
    bad = maker.post("/api/v1/invoices/"+invoice_id+"/credit-notes", headers=csrf(maker),
        json={"idempotency_key":"cr-1","amount_ugx":200000,"reason":"Overcharge"})
    assert bad.status_code == 409
    first = maker.post("/api/v1/invoices/"+invoice_id+"/credit-notes", headers=csrf(maker),
        json={"idempotency_key":"cr-1","amount_ugx":30000,"reason":"Water overcharged"})
    assert first.status_code == 201, first.json
    repeat = maker.post("/api/v1/invoices/"+invoice_id+"/credit-notes", headers=csrf(maker),
        json={"idempotency_key":"cr-1","amount_ugx":30000,"reason":"Repeated"})
    assert repeat.status_code == 200
    wrong = maker.post("/api/v1/invoices/"+invoice_id+"/credit-notes", headers=csrf(maker),
        json={"idempotency_key":"cr-1","amount_ugx":10000,"reason":"Different payload"})
    assert wrong.status_code == 409
    inv = db.session.get(Invoice, invoice_id)
    assert inv.credit_ugx == 30000 and inv.total_ugx == 180000 and inv.paid_ugx == 0
    assert db.session.query(CreditNote).count() == 1
    assert db.session.query(LedgerEntry).filter_by(invoice_id=invoice_id).count() == 2
    pending = maker.post("/api/v1/payments/manual", headers=csrf(maker),json={
        "invoice_id":invoice_id,"amount_ugx":160000,"method":"CASH","idempotency_key":"cash-credits-1"})
    assert pending.status_code == 400
    summary = maker.get("/api/v1/reports/summary?month=2026-11")
    assert summary.json["credited_ugx"] == 30000
    assert summary.json["outstanding_on_invoices_ugx"] == 150000

def test_tenant_must_not_read_another_invoice_lines(app):
    owner = create_user("owner-lines@kats.test","OWNER")
    stranger = create_user("stranger-lines@kats.test","TENANT")
    lease_id = seed()
    staff = auth_client(app, owner)
    inv = staff.post("/api/v1/invoices",headers=csrf(staff),json={
        "lease_id":lease_id,"period_start":"2026-10-01","period_end":"2026-10-31",
        "due_date":"2026-10-05","total_ugx":160000})
    assert inv.status_code == 201
    invoice_id = inv.json["invoice"]["id"]
    outsider = auth_client(app, stranger)
    assert outsider.get("/api/v1/invoices/"+invoice_id+"/lines").status_code == 404
    assert outsider.get("/api/v1/invoices/"+invoice_id+"/credit-notes").status_code == 404
