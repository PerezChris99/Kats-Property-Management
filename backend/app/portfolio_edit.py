"""Audited, reversible portfolio metadata editing.

Room rent/deposit fields are listing prices only; signed lease terms are
immutable and may only change via a dated lease amendment.
"""
from flask import Blueprint,abort,jsonify,request
from sqlalchemy.exc import IntegrityError
from .api import roles,data,required_string,ugx,serialize,fail,audit,ROOM_STATES
from .extensions import db
from .models import Property,Building,Floor,Room

portfolio_api=Blueprint("portfolio_edit",__name__)
OPS=("OWNER","MANAGER","SUPER_ADMIN")

@portfolio_api.put("/properties/<property_id>")
@roles(*OPS)
def update_property(user,property_id):
    obj=data()
    prop=db.session.query(Property).filter_by(id=property_id).with_for_update().first()
    if not prop:abort(404)
    changes={}
    for field,limit in (("name",200),("address",400),("district",120)):
        if field in obj:
            new=required_string(obj,field,limit)
            old=getattr(prop,field)
            if new!=old:
                changes[field]={"from":old,"to":new}
                setattr(prop,field,new)
    if not changes:
        return fail("Supply at least one changed property field",400)
    audit(user,"property.update","property",prop.id,changes=changes)
    db.session.commit()
    return jsonify(property=serialize(prop,"id","name","address","district"))

@portfolio_api.put("/buildings/<building_id>")
@roles(*OPS)
def update_building(user,building_id):
    obj=data()
    building=db.session.query(Building).filter_by(id=building_id).with_for_update().first()
    if not building:abort(404)
    changes={}
    if "name" in obj:
        name=required_string(obj,"name",160)
        if name!=building.name:
            changes["name"]={"from":building.name,"to":name}
            building.name=name
    if "description" in obj:
        desc=obj["description"]
        if not isinstance(desc,str) or len(desc)>500:
            return fail("Building description must be no more than 500 characters")
        if desc!=building.description:
            changes["description"]={"from":building.description,"to":desc}
            building.description=desc
    if not changes:return fail("No changed building fields",400)
    try:
        audit(user,"building.update","building",building.id,changes=changes)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Another building has that name",409)
    return jsonify(building=serialize(building,"id","property_id","name","description"))

@portfolio_api.put("/floors/<floor_id>")
@roles(*OPS)
def update_floor(user,floor_id):
    obj=data()
    floor=db.session.query(Floor).filter_by(id=floor_id).with_for_update().first()
    if not floor:abort(404)
    changes={}
    if "level" in obj:
        level=obj["level"]
        if type(level) is not int or not -10<=level<=300:
            return fail("Floor level must be -10 through 300")
        if level!=floor.level:
            changes["level"]={"from":floor.level,"to":level}
            floor.level=level
    if "label" in obj:
        label=required_string(obj,"label",100)
        if label!=floor.label:
            changes["label"]={"from":floor.label,"to":label}
            floor.label=label
    if not changes:return fail("No changed floor fields",400)
    try:
        audit(user,"floor.update","floor",floor.id,changes=changes)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Another floor uses this level in the building",409)
    return jsonify(floor=serialize(floor,"id","building_id","level","label"))

@portfolio_api.put("/rooms/<room_id>/details")
@roles(*OPS)
def update_room_details(user,room_id):
    obj=data()
    room=db.session.query(Room).filter_by(id=room_id).with_for_update().first()
    if not room:abort(404)
    changes={}
    if "number" in obj:
        number=required_string(obj,"number",60)
        if number!=room.number:
            changes["number"]={"from":room.number,"to":number}
            room.number=number
    for field in ("rent_ugx","deposit_ugx"):
        if field in obj:
            amount=ugx(obj[field])
            if amount!=getattr(room,field):
                changes[field]={"from":getattr(room,field),"to":amount}
                setattr(room,field,amount)
    if not changes:return fail("No changed room fields",400)
    try:
        audit(user,"room.details_update","room",room.id,changes=changes,
              notice="Advertised room prices updated; signed lease financial terms remain unchanged")
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Duplicate room number at this property",409)
    return jsonify(room=serialize(room,"id","property_id","floor_id","number",
                                 "rent_ugx","deposit_ugx","status"),
                   notice="Existing lease rent and deposit terms remain unchanged.")
