from app.extensions import db
from app.models import Building, Floor, Property, Room, AuditLog
from conftest import create_user, auth_client, csrf

def test_building_floor_room_integrity_and_authorization(app):
    owner=create_user("build-owner@kats.test","OWNER")
    tenant=create_user("build-tenant@kats.test","TENANT")
    admin=auth_client(app,owner); outsider=auth_client(app,tenant)
    p1=Property(name="Main",address="Kampala",district="Kampala")
    p2=Property(name="Annex",address="Kampala",district="Kampala")
    db.session.add_all([p1,p2]);db.session.commit()
    assert outsider.get("/api/v1/buildings").status_code==403
    b=admin.post("/api/v1/buildings",json={"property_id":p1.id,"name":"Tower A"},
                 headers=csrf(admin))
    assert b.status_code==201,b.json
    building_id=b.json["building"]["id"]
    dup=admin.post("/api/v1/buildings",json={"property_id":p1.id,"name":"Tower A"},
                 headers=csrf(admin))
    assert dup.status_code==409
    floor=admin.post("/api/v1/floors",json={"building_id":building_id,"level":0,"label":"Ground"},
                    headers=csrf(admin))
    assert floor.status_code==201,floor.json
    floor_id=floor.json["floor"]["id"]
    assert admin.post("/api/v1/floors",json={"building_id":building_id,"level":0,"label":"Duplicate"},
                headers=csrf(admin)).status_code==409
    assert admin.post("/api/v1/floors",json={"building_id":building_id,"level":True,"label":"Invalid"},
                headers=csrf(admin)).status_code==400
    wrong=admin.post("/api/v1/rooms",json={"property_id":p2.id,"floor_id":floor_id,
                 "number":"101","rent_ugx":150000},headers=csrf(admin))
    assert wrong.status_code==409
    good=admin.post("/api/v1/rooms",json={"property_id":p1.id,"floor_id":floor_id,
               "number":"101","rent_ugx":150000},headers=csrf(admin))
    assert good.status_code==201,good.json
    room_id=good.json["room"]["id"]
    assert good.json["room"]["floor_id"]==floor_id
    wrongmove=admin.put("/api/v1/rooms/"+room_id+"/floor",json={
        "floor_id":"invalid","reason":"Wrong floor"},headers=csrf(admin))
    assert wrongmove.status_code==404
    clear=admin.put("/api/v1/rooms/"+room_id+"/floor",json={
        "floor_id":None,"reason":"Reassigning building"},headers=csrf(admin))
    assert clear.status_code==200,clear.json
    assert clear.json["room"]["floor_id"] is None
    assert db.session.query(AuditLog).filter_by(action="room.floor_update").count()==1
    assert admin.get("/api/v1/floors?property_id="+p2.id).json["total"]==0
