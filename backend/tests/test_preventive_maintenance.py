from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from app.extensions import db
from app.models import Property,Room,MaintenanceRequest,CaretakerAssignment
from app.maintenance_plan_models import MaintenancePlan,MaintenanceOccurrence
from app.preventive_maintenance import generate_due_maintenance
from conftest import create_user,auth_client,csrf

def test_preventive_maintenance_generation_idempotent_and_role_scoped(app):
    owner=create_user("plan-owner@kats.test","OWNER")
    caretaker=create_user("plan-caretaker@kats.test","CARETAKER")
    stranger=create_user("plan-outsider@kats.test","CARETAKER")
    p=Property(name="Tower",address="Kampala",district="Kampala")
    db.session.add(p);db.session.flush()
    room=Room(property_id=p.id,number="C1",rent_ugx=300000,status="OCCUPIED")
    db.session.add(room);db.session.flush()
    db.session.add(CaretakerAssignment(room_id=room.id,caretaker_user_id=caretaker.id))
    db.session.commit()
    today=datetime.now(ZoneInfo("Africa/Kampala")).date()
    owner_cli=auth_client(app,owner)
    cr=owner_cli.post("/api/v1/maintenance/plans",headers=csrf(owner_cli),json={
        "room_id":room.id,"title":"Water pressure check",
        "instructions":"Check pump and record faults.","priority":"HIGH",
        "cadence_days":30,"next_due_on":today.isoformat()})
    assert cr.status_code==201,cr.json
    plan_id=cr.json["plan"]["id"]
    assert auth_client(app,stranger).get("/api/v1/maintenance/plans").json["items"]==[]
    assert len(auth_client(app,caretaker).get("/api/v1/maintenance/plans").json["items"])==1
    a=generate_due_maintenance(today)
    b=generate_due_maintenance(today)
    assert a["generated"]==1 and b["generated"]==0
    assert db.session.query(MaintenanceOccurrence).count()==1
    assert db.session.query(MaintenanceRequest).filter_by(title="Scheduled: Water pressure check").count()==1
    assert owner_cli.post("/api/v1/maintenance/plans/"+plan_id+"/status",headers=csrf(owner_cli),json={
        "status":"PAUSED","reason":"Landlord approved suspension"}).status_code==200
    after=generate_due_maintenance(today+timedelta(days=31))
    assert after["generated"]==0
    assert owner_cli.get("/api/v1/maintenance/plans/"+plan_id+"/occurrences").json["total"]==1
