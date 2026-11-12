"""Account analytics are queried and grouped at the DB, never from demo arrays."""
from app.extensions import db
from app.models import User, Room, Invoice, Tenant
from conftest import auth_client
from test_demo_preview import load_seeder


def seeded(app, monkeypatch):
    demo = load_seeder()
    monkeypatch.setattr(demo,"assert_preview_database",lambda *args:None)
    monkeypatch.setattr(demo,"create_app",lambda:app)
    demo.seed()
    owner=db.session.query(User).filter_by(email="landlord@demo.kats.invalid").one()
    tenant=db.session.query(User).filter_by(email="tenant01@demo.kats.invalid").one()
    other=db.session.query(User).filter_by(email="tenant02@demo.kats.invalid").one()
    return auth_client(app,owner),auth_client(app,tenant),auth_client(app,other)


def test_landlord_charts_are_live_group_by_queries_and_reject_tenant(app,monkeypatch):
    owner,tenant,_other=seeded(app,monkeypatch)
    routes=(
        "occupancy","collections-by-property","monthly","tenant-overlap","property-scores"
    )
    for name in routes:
        url="/api/v1/analytics/landlord/"+name
        result=owner.get(url)
        assert result.status_code==200,(name,result.json)
        assert ("points" in result.json if name!="tenant-overlap" else
                set(("current","maintenance","both","total")).issubset(result.json))
        assert tenant.get(url).status_code==403
    original=owner.get("/api/v1/analytics/landlord/occupancy").json
    total=sum(point["value"] for point in original["points"])
    assert total==33
    status=next(point["value"] for point in original["points"]
                if point["name"]=="Occupied")
    room=db.session.query(Room).filter_by(status="OCCUPIED").first()
    room.status="VACANT"
    db.session.commit()
    refreshed=owner.get("/api/v1/analytics/landlord/occupancy").json
    assert sum(point["value"] for point in refreshed["points"])==33
    assert next(point["value"] for point in refreshed["points"]
                if point["name"]=="Occupied")==status-1
    score=owner.get("/api/v1/analytics/landlord/property-scores").json
    assert len(score["points"])==3
    assert all(0<=row["occupancy"]<=100 for row in score["points"])
    venn=owner.get("/api/v1/analytics/landlord/tenant-overlap").json
    assert 0<=venn["both"]<=min(venn["current"],venn["maintenance"])
    assert venn["total"]==30


def test_tenant_charts_are_scoped_and_update_from_real_invoices(app,monkeypatch):
    owner,tenant,other=seeded(app,monkeypatch)
    route_names=("payment-status","applied-payments","balance-trend")
    for name in route_names:
        path="/api/v1/analytics/tenant/"+name
        response=tenant.get(path)
        assert response.status_code==200,(name,response.json)
        assert response.json["unit"] in ("UGX","invoices")
        assert owner.get(path).status_code==403
        assert other.get(path).status_code==200
    before=tenant.get("/api/v1/analytics/tenant/balance-trend").json["points"]
    other_before=other.get("/api/v1/analytics/tenant/balance-trend").json["points"]
    assert len(before)==2 and len(other_before)==2
    target_id=(db.session.query(Invoice.id)
               .join(Tenant, Invoice.tenant_id==Tenant.id)
               .filter(Tenant.user_id==db.session.query(User.id).filter_by(
                   email="tenant01@demo.kats.invalid").scalar())
               .first()[0])
    inv=db.session.get(Invoice,target_id)
    increment=min(1000,inv.total_ugx-inv.paid_ugx-inv.credit_ugx)
    if increment:
        inv.paid_ugx+=increment
    else:
        inv.paid_ugx-=1000
        increment=-1000
    db.session.commit()
    after=tenant.get("/api/v1/analytics/tenant/balance-trend").json["points"]
    other_after=other.get("/api/v1/analytics/tenant/balance-trend").json["points"]
    assert before!=after
    assert other_before==other_after
    assert sum(row["value"] for row in tenant.get(
        "/api/v1/analytics/tenant/payment-status").json["points"])==2


def test_new_chart_urls_are_denied_without_authentication(client):
    for path in ("/api/v1/analytics/landlord/occupancy",
                 "/api/v1/analytics/tenant/payment-status"):
        assert client.get(path).status_code==401
