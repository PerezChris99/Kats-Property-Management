"""Building/floor management without reassigning legacy occupied rooms."""
from flask import Blueprint, abort, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from .api import roles, data, required_string, fail, serialize, list_page, audit
from .extensions import db
from .models import Building, Floor, Property, Room

hierarchy_api=Blueprint("hierarchy",__name__)
OPS=("OWNER","MANAGER","SUPER_ADMIN")
STAFF=("OWNER","MANAGER","ACCOUNTANT","SUPER_ADMIN")

@hierarchy_api.get("/buildings")
@roles(*STAFF)
def buildings(user):
    query=db.session.query(Building)
    if request.args.get("property_id"):
        query=query.filter_by(property_id=request.args["property_id"])
    records=list_page(Building,query.order_by(Building.name))
    return jsonify(items=[serialize(b,"id","property_id","name","description","created_at") for b in records.items],
                   total=records.total)

@hierarchy_api.post("/buildings")
@roles(*OPS)
def create_building(user):
    obj=data()
    property_id=required_string(obj,"property_id")
    if not db.session.get(Property,property_id):
        abort(404)
    name=required_string(obj,"name",160)
    description=obj.get("description")
    if description is not None and (not isinstance(description,str) or len(description)>500):
        return fail("Description must be at most 500 characters")
    building=Building(property_id=property_id,name=name,description=description)
    db.session.add(building)
    try:
        db.session.flush()
        audit(user,"building.create","building",building.id,property_id=property_id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Building name already exists at this property",409)
    return jsonify(building=serialize(building,"id","property_id","name")),201

@hierarchy_api.get("/floors")
@roles(*STAFF)
def floors(user):
    query=db.session.query(Floor)
    if request.args.get("building_id"):
        query=query.filter_by(building_id=request.args["building_id"])
    if request.args.get("property_id"):
        query=query.join(Building,Building.id==Floor.building_id).filter(
            Building.property_id==request.args["property_id"])
    records=list_page(Floor,query.order_by(Floor.level))
    return jsonify(items=[serialize(f,"id","building_id","level","label","created_at") for f in records.items],
                   total=records.total)

@hierarchy_api.post("/floors")
@roles(*OPS)
def create_floor(user):
    obj=data()
    building_id=required_string(obj,"building_id")
    building=db.session.get(Building,building_id)
    if not building:
        abort(404)
    level=obj.get("level")
    if type(level) is not int or not -10<=level<=300:
        return fail("Floor level must be an integer between -10 and 300")
    label=required_string(obj,"label",100)
    record=Floor(building_id=building_id,level=level,label=label)
    db.session.add(record)
    try:
        db.session.flush()
        audit(user,"floor.create","floor",record.id,building_id=building_id,level=level)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Floor level already exists in this building",409)
    return jsonify(floor=serialize(record,"id","building_id","level","label")),201

@hierarchy_api.put("/rooms/<room_id>/floor")
@roles(*OPS)
def move_room_to_floor(user,room_id):
    obj=data()
    reason=required_string(obj,"reason",500)
    room=db.session.query(Room).filter_by(id=room_id).with_for_update().first()
    if not room:
        abort(404)
    floor_id=obj.get("floor_id")
    if floor_id is not None and (not isinstance(floor_id,str) or not floor_id):
        return fail("floor_id must be null or a valid floor ID")
    if floor_id:
        floor=db.session.get(Floor,floor_id)
        if not floor:
            abort(404)
        building=db.session.get(Building,floor.building_id)
        if building.property_id!=room.property_id:
            return fail("A room cannot be assigned to a floor from another property",409)
    previous=room.floor_id
    room.floor_id=floor_id
    audit(user,"room.floor_update","room",room.id,previous_floor_id=previous,
          floor_id=floor_id,reason=reason)
    db.session.commit()
    return jsonify(room=serialize(room,"id","property_id","floor_id","number"))
