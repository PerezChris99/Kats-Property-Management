"""Existing single-owner dashboards extended with SQL-backed portfolio and receipt history."""
from datetime import datetime, timezone
from app.extensions import db
from app.models import User, Room, Tenant, Invoice, Payment, Property
from test_workspace_analytics import seeded


def test_portfolio_counts_are_live_and_tenant_denied(app,monkeypatch):
    owner,tenant,_ = seeded(app,monkeypatch)
    path="/api/v1/analytics/landlord/portfolio"
    response=owner.get(path)
    assert response.status_code==200,response.json
    assert tenant.get(path).status_code==403
    points=response.json["points"]
    assert len(points)==3
    assert sum(item["value"] for item in points)==33
    assert all("id" in item and "district" in item for item in points)
    room=db.session.query(Room).filter_by(status="OCCUPIED").first()
    original=owner.get(path).json
    room.status="VACANT"
    db.session.commit()
    changed=owner.get(path).json
    before={item["id"]:item for item in original["points"]}
    after={item["id"]:item for item in changed["points"]}
    assert after[room.property_id]["occupied"]==before[room.property_id]["occupied"]-1
    assert after[room.property_id]["vacant"]==before[room.property_id]["vacant"]+1
    assert sum(item["value"] for item in changed["points"])==33


def test_tenant_verified_history_is_private_and_live(app,monkeypatch):
    owner,first,second=seeded(app,monkeypatch)
    path="/api/v1/analytics/tenant/payment-history"
    assert owner.get(path).status_code==403
    first_response=first.get(path)
    second_before=second.get(path)
    assert first_response.status_code==200 and second_before.status_code==200
    assert first_response.json["unit"]=="UGX"
    assert all(set(item)=={"name","value"} for item in first_response.json["points"])
    tenant_user=db.session.query(User).filter_by(email="tenant01@demo.kats.invalid").one()
    payment=(db.session.query(Payment).join(Invoice,Invoice.id==Payment.invoice_id)
             .join(Tenant,Tenant.id==Invoice.tenant_id)
             .filter(Tenant.user_id==tenant_user.id).first())
    assert payment is not None
    payment.status="RECONCILED"
    payment.reversed_at=None
    payment.settled_at=datetime(2026,10,10,tzinfo=timezone.utc)
    db.session.commit()
    after=first.get(path)
    assert after.status_code==200
    assert any(x["name"]=="2026-10" and x["value"]>=payment.amount_ugx
               for x in after.json["points"])
    assert second.get(path).json==second_before.json


def test_new_analytics_require_authentication(client):
    assert client.get("/api/v1/analytics/landlord/portfolio").status_code==401
    assert client.get("/api/v1/analytics/tenant/payment-history").status_code==401
