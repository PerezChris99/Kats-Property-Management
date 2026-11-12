"""SQL-backed searching must be literal, bounded and scope-aware."""
from app.extensions import db
from app.models import Tenant, Invoice, User
from conftest import auth_client
from test_workspace_analytics import seeded


def test_search_matches_records_beyond_first_page(app, monkeypatch):
    owner, tenant, other = seeded(app, monkeypatch)
    names = db.session.query(Tenant).order_by(Tenant.full_name).all()
    assert len(names) >= 25
    target = names[-1]
    target.full_name = "DistinctiveNameForSearch"
    db.session.commit()
    response = owner.get("/api/v1/tenants?page=1&page_size=5&q=DistinctiveNameForSearch")
    assert response.status_code == 200, response.json
    assert [item["id"] for item in response.json["items"]] == [target.id]
    assert owner.get("/api/v1/tenants?q=%25x").status_code == 200
    assert owner.get("/api/v1/tenants?q=" + "a"*101).status_code == 400
    assert owner.get("/api/v1/tenants?q=a").status_code == 400
    assert tenant.get("/api/v1/tenants?q=DistinctiveNameForSearch").status_code == 403


def test_invoice_search_never_crosses_tenant_boundary(app, monkeypatch):
    owner, tenant, other = seeded(app, monkeypatch)
    first_user = db.session.query(User).filter_by(email="tenant01@demo.kats.invalid").one()
    second_user = db.session.query(User).filter_by(email="tenant02@demo.kats.invalid").one()
    linked = {user.id: db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
              for user in (first_user, second_user)}
    first = db.session.query(Invoice).filter_by(tenant_id=linked[first_user.id]).first()
    second = db.session.query(Invoice).filter_by(tenant_id=linked[second_user.id]).first()
    assert first and second
    secret = second.invoice_number
    response = tenant.get("/api/v1/invoices?q=" + secret)
    assert response.status_code == 200
    assert response.json["items"] == []
    assert any(item["id"] == second.id for item in owner.get(
        "/api/v1/invoices?q=" + secret).json["items"])
    assert any(item["id"] == second.id for item in other.get(
        "/api/v1/invoices?q=" + secret).json["items"])
    assert tenant.get("/api/v1/invoices?q=" + "b"*101).status_code == 400
