"""Maintenance aging analytics must be live and staff-only."""
from datetime import datetime, timedelta, timezone
from app.extensions import db
from app.models import MaintenanceRequest
from test_workspace_analytics import seeded


def test_maintenance_aging_is_live_and_role_scoped(app,monkeypatch):
    owner, tenant, other = seeded(app,monkeypatch)
    path="/api/v1/operations/maintenance-aging"
    before=owner.get(path)
    assert before.status_code==200, before.json
    assert "points" in before.json
    assert tenant.get(path).status_code==403
    assert other.get(path).status_code==403
    ticket=db.session.query(MaintenanceRequest).filter(MaintenanceRequest.status.in_(
        ["OPEN","ASSIGNED","IN_PROGRESS","ON_HOLD"])).first()
    assert ticket is not None
    ticket.priority="URGENT"
    ticket.created_at=datetime.now(timezone.utc)-timedelta(days=13)
    db.session.commit()
    after=owner.get(path)
    assert after.status_code==200
    assert any(p["priority"]=="URGENT" and p["age"]=="8+ days"
               and p["value"]>=1 for p in after.json["points"])
    assert "NOT contractually agreed SLA" in after.json["method"]


def test_maintenance_aging_denies_anonymous(client):
    assert client.get("/api/v1/operations/maintenance-aging").status_code==401
