"""Single-business equipment register with staff writes and assignment-limited caretaker reads."""
from datetime import date
from flask import Blueprint, abort, jsonify, request
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from .api import roles, data, required_string, fail, audit
from .extensions import db
from .models import Property, Room, CaretakerAssignment
from .asset_models import PropertyAsset

asset_api = Blueprint("asset_api", __name__)
OPERATORS = ("OWNER","MANAGER","SUPER_ADMIN")
READERS = (*OPERATORS, "ACCOUNTANT", "CARETAKER")
STATES = {"IN_SERVICE","NEEDS_SERVICE","OUT_OF_SERVICE","RETIRED"}

def item(asset):
    return {
        "id":asset.id,"property_id":asset.property_id,"room_id":asset.room_id,
        "name":asset.name,"category":asset.category,"serial_reference":asset.serial_reference,
        "status":asset.status,"description":asset.description,
        "next_service_on":asset.next_service_on.isoformat() if asset.next_service_on else None,
    }

def optional_service_date(value):
    if value in ("",None):
        return None
    if not isinstance(value,str) or len(value)!=10:
        abort(400,description="Service date must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        abort(400,description="Invalid service date")

@asset_api.get("/operations/assets")
@roles(*READERS)
def list_assets(user):
    try:
        page=int(request.args.get("page","1"))
        page_size=int(request.args.get("page_size","25"))
    except (ValueError,TypeError):
        abort(400,description="Invalid pagination")
    if not 1<=page<=200 or not 1<=page_size<=100:
        abort(400,description="Invalid pagination")
    query=db.session.query(PropertyAsset)
    if user.role=="CARETAKER":
        assigned=db.session.query(CaretakerAssignment.room_id).filter_by(caretaker_user_id=user.id)
        query=query.filter(PropertyAsset.room_id.in_(assigned))
    property_id=request.args.get("property_id","").strip()
    if property_id:
        if len(property_id)>36:
            abort(400,description="Invalid property ID")
        query=query.filter(PropertyAsset.property_id==property_id)
    term=request.args.get("q","").strip()
    if term:
        if not 2<=len(term)<=80:
            abort(400,description="Search requires 2–80 characters")
        escaped=term.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
        query=query.filter(or_(
            PropertyAsset.name.ilike("%"+escaped+"%",escape="\\"),
            PropertyAsset.category.ilike("%"+escaped+"%",escape="\\")
        ))
    count=query.count()
    records=(query.order_by(PropertyAsset.name,PropertyAsset.id)
             .offset((page-1)*page_size).limit(page_size).all())
    return jsonify(items=[item(record) for record in records],total=count,page=page,page_size=page_size)

@asset_api.post("/operations/assets")
@roles(*OPERATORS)
def create_asset(user):
    obj=data()
    prop=db.session.get(Property,required_string(obj,"property_id",36))
    if not prop:
        abort(404,description="Property not found")
    room_id=obj.get("room_id")
    if room_id:
        if not isinstance(room_id,str) or len(room_id)>36:
            return fail("Invalid room ID")
        room=db.session.get(Room,room_id)
        if not room or room.property_id!=prop.id:
            return fail("Room does not belong to this property",409)
    raw_status=obj.get("status","IN_SERVICE")
    if not isinstance(raw_status,str) or raw_status not in STATES:
        return fail("Invalid asset status")
    raw_serial=obj.get("serial_reference")
    if raw_serial is not None and (not isinstance(raw_serial,str) or len(raw_serial)>120):
        return fail("Invalid serial reference")
    description=obj.get("description","")
    if not isinstance(description,str) or len(description)>1000:
        return fail("Description must be text no longer than 1000 characters")
    record=PropertyAsset(
        property_id=prop.id,room_id=room_id or None,
        name=required_string(obj,"name",160),
        category=required_string(obj,"category",50),
        description=description,
        serial_reference=(raw_serial.strip() or None) if raw_serial is not None else None,
        status=raw_status,
        next_service_on=optional_service_date(obj.get("next_service_on"))
    )
    db.session.add(record)
    try:
        db.session.flush()
        audit(user,"asset.create","property_asset",record.id,property_id=record.property_id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail("Asset with this property serial reference already exists",409)
    return jsonify(asset=item(record)),201

@asset_api.patch("/operations/assets/<asset_id>")
@roles(*OPERATORS)
def update_asset(user,asset_id):
    obj=data()
    reason=required_string(obj,"reason",500)
    record=db.session.query(PropertyAsset).filter_by(id=asset_id).with_for_update().first()
    if record is None:
        abort(404)
    changes={}
    for name,limit in (("name",160),("category",50)):
        if name in obj:
            value=required_string(obj,name,limit)
            if value!=getattr(record,name):
                changes[name]={"from":getattr(record,name),"to":value}
                setattr(record,name,value)
    if "status" in obj:
        status=obj["status"]
        if not isinstance(status,str) or status not in STATES:
            return fail("Invalid asset status")
        if status!=record.status:
            changes["status"]={"from":record.status,"to":status}
            record.status=status
    if "next_service_on" in obj:
        next_date=optional_service_date(obj["next_service_on"])
        if next_date!=record.next_service_on:
            changes["next_service_on"]={
                "from":record.next_service_on.isoformat() if record.next_service_on else None,
                "to":next_date.isoformat() if next_date else None}
            record.next_service_on=next_date
    if not changes:
        return fail("No asset changes supplied")
    audit(user,"asset.update","property_asset",record.id,
          property_id=record.property_id,reason=reason,changes=changes)
    db.session.commit()
    return jsonify(asset=item(record))
