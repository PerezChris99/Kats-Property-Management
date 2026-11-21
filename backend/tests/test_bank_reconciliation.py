"""Bank statement CSV, atomic reconciliation and dual-review integration."""
from datetime import date
from app.extensions import db
from app.finance.bank_models import BankStatement, BankStatementLine, BankMatch
from app.finance.gl_models import GLLine, GLEvent
from app.finance.bank import BankEvidenceError, parse_bank_csv
from app.finance.ledger import post_event
from conftest import create_user, auth_client, csrf

SOURCE = (
    "date,reference,description,inflow_ugx,outflow_ugx\n"
    "2025-02-10,BNK-1,Deposit from tenants,1000,0\n"
)


def users(app):
    owner = create_user("bank-owner@example.test", "OWNER")
    accountant = create_user("bank-accountant@example.test", "ACCOUNTANT")
    tenant = create_user("bank-tenant@example.test", "TENANT")
    return owner, accountant, tenant


def test_statement_import_and_two_person_reconciliation_posts_cash_to_bank_only_once(app):
    owner, accountant, tenant = users(app)
    entry1 = post_event("payment:test-one", "RECEIPT", date(2025, 2, 10),
                        [("CASH_CLEARING", 600, 0), ("RENT_RECEIVABLE", 0, 600)])
    entry2 = post_event("payment:test-two", "RECEIPT", date(2025, 2, 10),
                        [("CASH_CLEARING", 400, 0), ("RENT_RECEIVABLE", 0, 400)])
    db.session.commit()
    first = db.session.query(GLEvent).filter_by(event_key="payment:test-one").one()
    second = db.session.query(GLEvent).filter_by(event_key="payment:test-two").one()
    uploader = auth_client(app, owner)
    reviewer = auth_client(app, accountant)
    tenant_client = auth_client(app, tenant)
    submitted = uploader.post("/api/v1/finance/bank-statements", json={
        "bank_label": "Test bank", "account_mask": "****1234",
        "start_date": "2025-02-01", "end_date": "2025-02-28",
        "opening_ugx": 0, "closing_ugx": 1000, "csv_text": SOURCE,
    }, headers=csrf(uploader))
    assert submitted.status_code == 201, submitted.get_json()
    statement_id = submitted.json["statement_id"]
    before = uploader.get("/api/v1/finance/bank-statements/" + statement_id)
    assert before.status_code == 200
    assert not before.json["can_close"]
    assert len(before.json["exceptions"]) == 1
    line_id = before.json["exceptions"][0]["id"]
    assert tenant_client.get("/api/v1/finance/bank-statements").status_code == 403

    candidate = uploader.get(f"/api/v1/finance/bank-statements/{statement_id}/candidates/{line_id}")
    assert candidate.status_code == 200
    assert {r["event_key"] for r in candidate.json["items"]} >= {
        "payment:test-one", "payment:test-two"}

    for event, amount in ((first,600),(second,400)):
        match = uploader.post(f"/api/v1/finance/bank-statements/{statement_id}/matches",
                              json={"line_id":line_id,"gl_event_id":event.id,
                                    "signed_ugx":amount},
                              headers=csrf(uploader))
        assert match.status_code == 201, match.get_json()
        self_review = uploader.post("/api/v1/finance/bank-matches/" +
                                    match.json["match_id"] + "/review",
                                    json={"decision":"APPROVE","reason":"not independent"},
                                    headers=csrf(uploader))
        assert self_review.status_code == 403
        accepted = reviewer.post("/api/v1/finance/bank-matches/" +
                                  match.json["match_id"] + "/review",
                                  json={"decision":"APPROVE","reason":"verified imported bank statement"},
                                  headers=csrf(reviewer))
        assert accepted.status_code == 200, accepted.get_json()
        if amount == 600:
            assert not db.session.query(GLEvent.id).filter(
                GLEvent.event_key.startswith("bank-settlement:")).first()

    reconciled = reviewer.get("/api/v1/finance/bank-statements/" + statement_id)
    assert reconciled.status_code == 200
    assert reconciled.json["can_close"]
    assert reconciled.json["book_closing_ugx"] == 1000
    assert reconciled.json["closing_difference_ugx"] == 0
    assert not reconciled.json["exceptions"]
    assert db.session.query(GLEvent).filter(
        GLEvent.event_key.startswith("bank-settlement:")).count() == 1

    cannot_self_close = uploader.post(
        "/api/v1/finance/bank-statements/" + statement_id + "/close",
        json={"reason":"invalid self-review"},headers=csrf(uploader))
    assert cannot_self_close.status_code == 403
    close = reviewer.post("/api/v1/finance/bank-statements/" + statement_id + "/close",
                          json={"reason":"bank statement verified against posted GL"},
                          headers=csrf(reviewer))
    assert close.status_code == 200
    assert close.json["state"] == "RECONCILED"
    assert db.session.query(BankMatch).filter_by(state="APPROVED").count() == 2
    assert db.session.query(BankStatement).filter_by(state="RECONCILED").count() == 1


def test_statement_import_does_not_fake_balance_or_external_settlement(app):
    owner, accountant, _ = users(app)
    uploader = auth_client(app, owner)
    wrong = uploader.post("/api/v1/finance/bank-statements", json={
        "bank_label":"Test bank","account_mask":"****1234",
        "start_date":"2025-02-01","end_date":"2025-02-28",
        "opening_ugx":0,"closing_ugx":2000,"csv_text":SOURCE},
        headers=csrf(uploader))
    assert wrong.status_code == 400
    assert db.session.query(BankStatement).count() == 0
    assert db.session.query(GLEvent).count() == 0


def test_bank_csv_rejects_ambiguous_or_invalid_amount_signs(app):
    text = "date,reference,description,inflow_ugx,outflow_ugx\n2025-02-10,dup,Bad,100,20\n"
    from app.finance.bank import parse_bank_csv
    import pytest
    with pytest.raises(BankEvidenceError,match="exactly one"):
        parse_bank_csv(text,date(2025,2,1),date(2025,2,28))
    text = "date,reference,description,inflow_ugx,outflow_ugx\n2025-02-10,bad,Bad,1.00,0\n"
    with pytest.raises(BankEvidenceError,match="integer"):
        parse_bank_csv(text,date(2025,2,1),date(2025,2,28))


def test_unmatched_bank_debit_requires_real_bank_gl_credit_before_matching(app):
    owner, accountant, _ = users(app)
    uploader = auth_client(app,owner)
    transfer = uploader.post("/api/v1/finance/bank-statements", json={
        "bank_label":"Test bank","account_mask":"****1234",
        "start_date":"2025-02-01","end_date":"2025-02-28",
        "opening_ugx":1000,"closing_ugx":500,
        "csv_text":"date,reference,description,inflow_ugx,outflow_ugx\n"
                   "2025-02-10,DEBIT-1,External withdrawal,0,500\n"},
        headers=csrf(uploader))
    assert transfer.status_code == 201,transfer.get_json()
    bank_id = transfer.json["statement_id"]
    report = uploader.get("/api/v1/finance/bank-statements/" + bank_id).json
    line_id = report["exceptions"][0]["id"]
    candidates = uploader.get(
        f"/api/v1/finance/bank-statements/{bank_id}/candidates/{line_id}")
    assert candidates.status_code == 200 and candidates.json["items"] == []
    assert not report["can_close"]


def test_second_bank_account_cannot_use_first_accounts_gl_balance(app):
    """The single BANK GL account cannot prove separate financial balances."""
    owner, _, _ = users(app)
    client = auth_client(app, owner)
    def upload(mask):
        return client.post("/api/v1/finance/bank-statements", json={
            "bank_label": "Test bank", "account_mask": mask,
            "start_date": "2025-02-01", "end_date": "2025-02-28",
            "opening_ugx": 0, "closing_ugx": 1000, "csv_text": SOURCE,
        }, headers=csrf(client))
    first = upload("****1234")
    assert first.status_code == 201, first.get_json()
    second = upload("****9999")
    assert second.status_code == 201, second.get_json()
    post_event("opening:first-bank", "OPENING_BALANCES", date(2025, 1, 31),
               [("BANK", 500, 0), ("OWNER_EQUITY", 0, 500)])
    db.session.commit()
    def report(result):
        return client.get("/api/v1/finance/bank-statements/" + result.json["statement_id"]).json
    assert report(first)["book_opening_ugx"] == 500
    other = report(second)
    assert other["book_opening_ugx"] == 0
    assert other["statement"]["book_code"] != "BANK"
