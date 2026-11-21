from app.extensions import db
from app.finance.gl_models import GLLine
from app.models import Lease, Tenant
from conftest import auth_client, create_user, csrf
from test_invoice_credits import seed


def test_lump_sum_receipt_allocations_replay_isolation_and_correction(app):
    owner = auth_client(app, create_user("advance-owner@example.test", "OWNER"))
    checker = auth_client(app, create_user("advance-reviewer@example.test", "ACCOUNTANT"))
    tenant = create_user("advance-tenant@example.test", "TENANT")
    outsider = auth_client(app, create_user("other-tenant@example.test", "TENANT"))
    lease = db.session.get(Lease, seed())
    db.session.get(Tenant, lease.tenant_id).user_id = tenant.id
    db.session.commit()
    def post(client, path, payload):
        return client.post("/api/v1/" + path, json=payload, headers=csrf(client))
    payload = dict(lease_id=lease.id, method="BANK_TRANSFER", amount_ugx=1500000,
                   reference="statement-001", idempotency_key="receipt-001")
    receipt = post(owner, "rent-advances", payload)
    assert receipt.status_code == 201, receipt.json
    path = "rent-advances/" + receipt.json["id"]
    assert post(owner, "rent-advances", payload).status_code == 200
    assert post(owner, path + "/approve", {}).status_code == 409
    assert post(checker, path + "/approve", {}).json["available_ugx"] == 1500000
    assert outsider.get("/api/v1/rent-advances").json["items"] == []
    assert outsider.get("/api/v1/" + path + "/receipt.pdf").status_code == 404
    assert auth_client(app, tenant).get("/api/v1/" + path + "/receipt.pdf").data.startswith(b"%PDF")
    assert auth_client(app, tenant).get("/api/v1/rent-advances").json["items"][0]["reference"] == "statement-001"
    applied = []
    for month in ("05", "06"):
        response = post(owner, "invoices", dict(lease_id=lease.id, period_start=f"2026-{month}-01",
                        period_end=f"2026-{month}-28", due_date=f"2026-{month}-05", total_ugx=500000))
        invoice_id = response.json["invoice"]["id"]
        command = dict(invoice_id=invoice_id, amount_ugx=500000, idempotency_key="allocate-" + month)
        result = post(owner, path + "/apply", command)
        assert result.status_code == 201, result.json
        assert post(owner, path + "/apply", command).json["payment_id"] == result.json["payment_id"]
        applied.append(result.json["payment_id"])
    assert result.json["advance"]["available_ugx"] == 500000
    assert db.session.query(GLLine).filter_by(account_code="CASH_CLEARING", debit_ugx=1500000).count() == 1
    assert post(owner, path + "/reverse", {"reason": "Correction"}).status_code == 409
    for payment_id in applied:
        assert post(checker, "payments/" + payment_id + "/reverse", {"reason": "Incorrect invoice"}).status_code == 200
    assert post(checker, path + "/reverse", {"reason": "Incorrect receipt"}).json["status"] == "REVERSED"
