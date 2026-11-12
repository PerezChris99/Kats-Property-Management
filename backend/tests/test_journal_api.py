"""Receipt journal integration at the actual approval/reversal API boundary."""
import uuid
from app.extensions import db
from app.models import Invoice, Payment
from app.journal_models import JournalEvent, JournalLine
from conftest import auth_client, create_user, csrf
from test_workspace_analytics import seeded


def test_manual_approval_and_reversal_post_balanced_journal(app,monkeypatch):
    owner, tenant, other = seeded(app,monkeypatch)
    accountant_user=create_user("journal-reviewer@example.invalid","ACCOUNTANT")
    reviewer=auth_client(app,accountant_user)
    invoice=db.session.query(Invoice).filter(
        Invoice.total_ugx>Invoice.paid_ugx+Invoice.credit_ugx).first()
    assert invoice is not None
    owner_user=db.session.query(Payment).first().created_by
    record=Payment(invoice_id=invoice.id,amount_ugx=100,
                   method="CASH",status="PENDING_REVIEW",
                   created_by=owner_user,idempotency_key=str(uuid.uuid4()))
    db.session.add(record)
    db.session.commit()
    response=reviewer.post("/api/v1/payments/"+record.id+"/approve",headers=csrf(reviewer))
    assert response.status_code==200,response.get_json(silent=True)
    assert response.json["payment"]["status"]=="RECONCILED"
    assert tenant.get("/api/v1/finance/journal-control").status_code==403
    summary=owner.get("/api/v1/finance/journal-control")
    assert summary.status_code==200,summary.get_json(silent=True)
    assert summary.json["balanced"] is True
    assert summary.json["total_debit_ugx"]==100
    assert summary.json["total_credit_ugx"]==100
    reversal=owner.post("/api/v1/payments/"+record.id+"/reverse",
        json={"reason":"Test correction"},headers=csrf(owner))
    assert reversal.status_code==200,reversal.get_json(silent=True)
    after=owner.get("/api/v1/finance/journal-control").json
    assert after["balanced"] is True
    assert after["total_debit_ugx"]==200
    assert after["total_credit_ugx"]==200
    assert db.session.query(JournalEvent).filter_by(source_payment_id=record.id).count()==2
    assert db.session.query(JournalLine).count()==4


def test_journal_control_anonymous_denied(client):
    assert client.get("/api/v1/finance/journal-control").status_code==401
