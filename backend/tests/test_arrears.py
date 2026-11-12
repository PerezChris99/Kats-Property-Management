"""Single-owner arrears report must match live balances and deny tenants."""
from datetime import date, timedelta
from app.extensions import db
from app.models import Invoice
from test_workspace_analytics import seeded


def test_aging_is_live_and_role_restricted(app,monkeypatch):
    owner, tenant, other = seeded(app, monkeypatch)
    summary=owner.get("/api/v1/finance/arrears-aging")
    assert summary.status_code==200,summary.get_json(silent=True)
    assert tenant.get("/api/v1/finance/arrears-aging").status_code==403
    assert other.get("/api/v1/finance/arrears-invoices").status_code==403
    assert summary.json["unit"]=="UGX"
    invoice=db.session.query(Invoice).filter(Invoice.status.in_(
        ["ISSUED","OVERDUE","PARTIALLY_PAID"])).first()
    assert invoice
    invoice.due_date=date.today()-timedelta(days=100)
    invoice.paid_ugx=0
    invoice.credit_ugx=0
    invoice.status="OVERDUE"
    db.session.commit()
    new=owner.get("/api/v1/finance/arrears-aging")
    assert new.status_code==200
    assert new.json["outstanding_ugx"] >= invoice.total_ugx
    assert new.json["overdue_invoices"] >= 1
    page=owner.get("/api/v1/finance/arrears-invoices?page=1&page_size=100")
    assert page.status_code==200,page.get_json(silent=True)
    assert any(x["invoice_id"]==invoice.id for x in page.json["items"])
    assert owner.get("/api/v1/finance/arrears-invoices?page_size=101").status_code==400
    assert owner.get("/api/v1/finance/arrears-invoices?page=bad").status_code==400


def test_anonymous_arrears_is_denied(client):
    assert client.get("/api/v1/finance/arrears-aging").status_code==401
    assert client.get("/api/v1/finance/arrears-invoices").status_code==401
