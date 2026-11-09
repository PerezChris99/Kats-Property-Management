from datetime import date
from app.extensions import db
from app.models import Property, Expense, ExpenseEvent
from conftest import create_user, auth_client, csrf

def test_expenses_require_independent_approval_and_reversible_audit(app):
    maker=create_user("expense-maker@kats.test","OWNER")
    checker=create_user("expense-checker@kats.test","ACCOUNTANT")
    tenant=create_user("expense-outsider@kats.test","TENANT")
    prop=Property(name="Verified Expenses",address="Kampala",district="Kampala")
    db.session.add(prop);db.session.commit()
    client=auth_client(app,maker); finance=auth_client(app,checker)
    payload={"property_id":prop.id,"category":"REPAIR","description":"Roof repaired",
             "amount_ugx":78000,"incurred_on":"2026-11-09","idempotency_key":"expense-command-100"}
    created=client.post("/api/v1/expenses",headers=csrf(client),json=payload)
    assert created.status_code==201,created.json
    expense_id=created.json["expense"]["id"]
    assert created.json["expense"]["status"]=="PENDING_APPROVAL"
    again=client.post("/api/v1/expenses",headers=csrf(client),json=payload)
    assert again.status_code==200
    wrong=client.post("/api/v1/expenses",headers=csrf(client),json={
        **payload,"amount_ugx":80000})
    assert wrong.status_code==409
    report=client.get("/api/v1/reports/summary?month=2026-11")
    assert report.status_code==200 and report.json["expenses_in_period_ugx"]==0
    self_review=client.post("/api/v1/expenses/"+expense_id+"/review",headers=csrf(client),
        json={"decision":"APPROVE","reason":"Checked owner invoice"})
    assert self_review.status_code==403
    approved=finance.post("/api/v1/expenses/"+expense_id+"/review",headers=csrf(finance),
        json={"decision":"APPROVE","reason":"Supplier invoice and work order checked"})
    assert approved.status_code==200,approved.json
    assert approved.json["expense"]["status"]=="APPROVED"
    assert client.get("/api/v1/reports/summary?month=2026-11").json["expenses_in_period_ugx"]==78000
    refused=finance.post("/api/v1/expenses/"+expense_id+"/reverse",headers=csrf(finance),
        json={"reason":"Wrong amount"})
    assert refused.status_code==403
    reversed_=client.post("/api/v1/expenses/"+expense_id+"/reverse",headers=csrf(client),
        json={"reason":"Duplicate claim detected"})
    assert reversed_.status_code==200,reversed_.json
    assert client.get("/api/v1/reports/summary?month=2026-11").json["expenses_in_period_ugx"]==0
    assert db.session.query(ExpenseEvent).filter_by(expense_id=expense_id).count()==3
    assert client.post("/api/v1/expenses/"+expense_id+"/reverse",headers=csrf(client),
        json={"reason":"Repeated reversal"}).status_code==200
    assert db.session.query(ExpenseEvent).filter_by(expense_id=expense_id).count()==3
    outsider=auth_client(app,tenant)
    assert outsider.get("/api/v1/expenses").status_code==403
    assert outsider.get("/api/v1/expenses/"+expense_id+"/events").status_code==403

def test_rejected_expenses_cannot_affect_cost_reports(app):
    owner=create_user("expense-owner-2@kats.test","OWNER")
    checker=create_user("expense-accountant-2@kats.test","ACCOUNTANT")
    property_=Property(name="Costs",address="Kampala",district="Kampala")
    db.session.add(property_);db.session.commit()
    cli=auth_client(app,owner);accountant=auth_client(app,checker)
    x=cli.post("/api/v1/expenses",headers=csrf(cli),json={
        "property_id":property_.id,"category":"SUPPLIES","description":"Unverified supplies",
        "amount_ugx":50000,"incurred_on":"2026-11-09","idempotency_key":"cost-invalid-1"})
    assert x.status_code==201
    id=x.json["expense"]["id"]
    rejected=accountant.post("/api/v1/expenses/"+id+"/review",headers=csrf(accountant),
        json={"decision":"REJECT","reason":"No supporting supplier documentation"})
    assert rejected.status_code==200
    assert db.session.get(Expense,id).status=="REJECTED"
    assert cli.get("/api/v1/reports/summary?month=2026-11").json["expenses_in_period_ugx"]==0
    assert cli.post("/api/v1/expenses/"+id+"/reverse",headers=csrf(cli),json={
        "reason":"Not allowed"}).status_code==409
