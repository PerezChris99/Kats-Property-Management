"""GL API maker-checker approval, reporting, and data-isolation regression."""
from app.extensions import db
from app.finance.gl_models import GLEvent, GLLine, GLOpeningBatch
from conftest import create_user, auth_client, csrf

CSV = "account_code,debit_ugx,credit_ugx\nBANK,900000,0\nOWNER_EQUITY,0,900000\n"


def test_opening_balance_csv_needs_independent_authorized_approval(app):
    owner = create_user("gl-owner@example.com", "OWNER")
    accountant = create_user("gl-accountant@example.com", "ACCOUNTANT")
    tenant = create_user("gl-tenant@example.com", "TENANT")
    owner_client = auth_client(app, owner)
    reviewer = auth_client(app, accountant)
    tenant_client = auth_client(app, tenant)

    unauthorized = tenant_client.post("/api/v1/finance/gl/opening-batches",
                                     json={"csv_text": CSV}, headers=csrf(tenant_client))
    assert unauthorized.status_code == 403
    submitted = owner_client.post("/api/v1/finance/gl/opening-batches",
                                  json={"effective_on": "2025-01-01", "csv_text": CSV,
                                        "note": "Approved historical opening trial balance"},
                                  headers=csrf(owner_client))
    assert submitted.status_code == 201, submitted.get_json()
    batch_id = submitted.json["batch"]["id"]
    assert db.session.query(GLEvent).count() == 0

    refused = owner_client.post(
        "/api/v1/finance/gl/opening-batches/" + batch_id + "/review",
        json={"decision": "APPROVE", "reason": "Self approval should fail"},
        headers=csrf(owner_client))
    assert refused.status_code == 403
    completed = reviewer.post(
        "/api/v1/finance/gl/opening-batches/" + batch_id + "/review",
        json={"decision": "APPROVE", "reason": "Verified against approved trial balance"},
        headers=csrf(reviewer))
    assert completed.status_code == 200, completed.get_json()
    assert db.session.query(GLEvent).count() == 1
    assert db.session.query(GLLine).count() == 2
    assert db.session.get(GLOpeningBatch,batch_id).status == "POSTED"

    trial = owner_client.get("/api/v1/finance/gl/trial-balance")
    assert trial.status_code == 200, trial.get_json()
    assert trial.json["balanced"]
    assert trial.json["debit_ugx"] == trial.json["credit_ugx"] == 900000
    assert tenant_client.get("/api/v1/finance/gl/trial-balance").status_code == 403
    balance = reviewer.get("/api/v1/finance/gl/balance-sheet")
    assert balance.status_code == 200 and balance.json["balanced"]
    assert balance.json["assets_ugx"] == 900000
    assert balance.json["equity_ugx"] == 900000
    assert reviewer.get("/api/v1/finance/gl/detail").status_code == 200


def test_unbalanced_opening_import_refused_before_review(app):
    owner = create_user("gl-owner-import@example.com", "OWNER")
    client = auth_client(app, owner)
    bad = "account_code,debit_ugx,credit_ugx\nBANK,90,0\nOWNER_EQUITY,0,89\n"
    result = client.post("/api/v1/finance/gl/opening-batches",
                         json={"effective_on": "2025-01-01", "csv_text": bad,
                               "note": "Unbalanced"},
                         headers=csrf(client))
    assert result.status_code == 400, result.get_json()
    assert db.session.query(GLOpeningBatch).count() == 0
    assert db.session.query(GLEvent).count() == 0


def test_anon_gl_private_and_invalid_dates_refused(client, app):
    assert client.get("/api/v1/finance/gl/detail").status_code == 401
    owner = create_user("gl-check@example.com", "OWNER")
    signed = auth_client(app, owner)
    assert signed.get("/api/v1/finance/gl/trial-balance?through=invalid").status_code == 400
    assert signed.get("/api/v1/finance/gl/detail?page_size=1000").status_code == 400
