"""Read-only finance health queries and role isolation."""
from app.extensions import db
from app.models import Invoice, User
from conftest import auth_client
from test_workspace_analytics import seeded


def test_finance_health_is_read_only_and_role_restricted(app,monkeypatch):
    owner, tenant, other = seeded(app,monkeypatch)
    assert tenant.get("/api/v1/finance/reconciliation").status_code == 403
    assert other.get("/api/v1/finance/reconciliation").status_code == 403
    before = owner.get("/api/v1/finance/reconciliation")
    assert before.status_code == 200, before.json
    assert before.json["total_exceptions"] == 0
    invoice = db.session.query(Invoice).first()
    old = invoice.paid_ugx
    invoice.paid_ugx = old + 1 if invoice.paid_ugx + invoice.credit_ugx < invoice.total_ugx else old - 1
    db.session.commit()
    changed = owner.get("/api/v1/finance/reconciliation")
    assert changed.status_code == 200
    assert changed.json["total_exceptions"] >= 1
    assert any(x["invoice_id"] == invoice.id for x in changed.json["items"])
    assert db.session.get(Invoice,invoice.id).paid_ugx == invoice.paid_ugx
    assert owner.get("/api/v1/finance/reconciliation?page_size=101").status_code == 400
    assert owner.get("/api/v1/finance/reconciliation?page=invalid").status_code == 400


def test_finance_health_fails_closed_anonymously(client):
    assert client.get("/api/v1/finance/reconciliation").status_code == 401
