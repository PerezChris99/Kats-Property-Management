"""Permission-safe global search, including tenant boundary and wildcard behavior."""
from app.extensions import db
from app.models import Invoice, Tenant, User
from test_workspace_analytics import seeded


def test_global_search_role_scope_and_bounded_results(app,monkeypatch):
    owner, tenant, other = seeded(app,monkeypatch)
    invoice = db.session.query(Invoice).join(Tenant,Invoice.tenant_id==Tenant.id).join(
        User,Tenant.user_id==User.id).filter(User.email=="tenant02@demo.kats.invalid").first()
    assert invoice is not None
    phrase=invoice.invoice_number
    mine=other.get("/api/v1/workspace/search?q="+phrase)
    foreign=tenant.get("/api/v1/workspace/search?q="+phrase)
    staff=owner.get("/api/v1/workspace/search?q="+phrase)
    assert mine.status_code==foreign.status_code==staff.status_code==200
    assert any(result["value"]==invoice.id for result in mine.json["items"])
    assert not any(result["value"]==invoice.id for result in foreign.json["items"])
    assert any(result["value"]==invoice.id for result in staff.json["items"])
    assert all(item["path"].startswith("/") for item in staff.json["items"])
    assert len(staff.json["items"])<=32
    assert owner.get("/api/v1/workspace/search?q=a").status_code==400
    assert owner.get("/api/v1/workspace/search?q="+"b"*81).status_code==400
    assert owner.get("/api/v1/workspace/search?q=%25x").status_code==200


def test_global_search_requires_login(client):
    assert client.get("/api/v1/workspace/search?q=test").status_code==401
