"""Asset lifecycle tests for owner, tenant and assignment-limited caretaker accounts."""
from app.extensions import db
from app.models import Property,Room,CaretakerAssignment
from app.asset_models import PropertyAsset
from conftest import create_user,auth_client,csrf
from test_workspace_analytics import seeded


def test_owner_asset_creation_edit_and_tenant_denial(app,monkeypatch):
    owner,tenant,_ = seeded(app,monkeypatch)
    prop=db.session.query(Property).first()
    room=db.session.query(Room).filter_by(property_id=prop.id).first()
    assert prop and room
    body={"property_id":prop.id,"room_id":room.id,"name":"Water pump",
          "category":"PLUMBING","serial_reference":"PUMP-ABC-001",
          "next_service_on":"2027-01-10"}
    assert tenant.get("/api/v1/operations/assets").status_code==403
    assert tenant.post("/api/v1/operations/assets",json=body,headers=csrf(tenant)).status_code==403
    created=owner.post("/api/v1/operations/assets",json=body,headers=csrf(owner))
    assert created.status_code==201,created.json
    identifier=created.json["asset"]["id"]
    listed=owner.get("/api/v1/operations/assets")
    assert listed.status_code==200 and any(item["id"]==identifier for item in listed.json["items"])
    changed=owner.patch("/api/v1/operations/assets/"+identifier,
        json={"status":"NEEDS_SERVICE","reason":"Inspection found bearing noise"},
        headers=csrf(owner))
    assert changed.status_code==200,changed.json
    assert changed.json["asset"]["status"]=="NEEDS_SERVICE"
    assert db.session.get(PropertyAsset,identifier).status=="NEEDS_SERVICE"
    assert owner.patch("/api/v1/operations/assets/"+identifier,
        json={"status":"UNAPPROVED","reason":"Test"},headers=csrf(owner)).status_code==400
    assert owner.post("/api/v1/operations/assets",json=body,headers=csrf(owner)).status_code==409
    assert owner.get("/api/v1/operations/assets?page_size=101").status_code==400


def test_caretaker_assets_only_for_assigned_room(app,monkeypatch):
    owner,tenant,_=seeded(app,monkeypatch)
    caretaker=create_user("asset-care@example.invalid","CARETAKER")
    caretaker_client=auth_client(app,caretaker)
    rooms=db.session.query(Room).order_by(Room.id).limit(2).all()
    assert len(rooms)==2
    db.session.add(CaretakerAssignment(caretaker_user_id=caretaker.id,room_id=rooms[0].id))
    db.session.add_all([
      PropertyAsset(property_id=rooms[0].property_id,room_id=rooms[0].id,
                    name="Assigned room meter",category="UTILITY"),
      PropertyAsset(property_id=rooms[1].property_id,room_id=rooms[1].id,
                    name="Another room meter",category="UTILITY"),
      PropertyAsset(property_id=rooms[0].property_id,room_id=None,
                    name="Central generator",category="ELECTRICAL")
    ])
    db.session.commit()
    response=caretaker_client.get("/api/v1/operations/assets")
    assert response.status_code==200,response.json
    assert [x["name"] for x in response.json["items"]]==["Assigned room meter"]
    assert caretaker_client.post("/api/v1/operations/assets",json={
        "property_id":rooms[0].property_id,"name":"Unauthorized",
        "category":"UTILITY"},headers=csrf(caretaker_client)).status_code==403


def test_anonymous_cannot_access_assets(client):
    assert client.get("/api/v1/operations/assets").status_code==401
