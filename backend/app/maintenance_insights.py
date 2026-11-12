"""Operational maintenance aging, not a contractual SLA measurement."""
from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify
from sqlalchemy import case, func
from .api import roles
from .extensions import db
from .models import MaintenanceRequest

maintenance_insights_api = Blueprint("maintenance_insights",__name__)
STAFF = ("OWNER","MANAGER","ACCOUNTANT","SUPER_ADMIN")
OPEN = ("OPEN","ASSIGNED","IN_PROGRESS","ON_HOLD")


@maintenance_insights_api.get("/operations/maintenance-aging")
@roles(*STAFF)
def maintenance_aging(_user):
    now = datetime.now(timezone.utc)
    age = case(
        (MaintenanceRequest.created_at >= now - timedelta(days=2), "0–2 days"),
        (MaintenanceRequest.created_at >= now - timedelta(days=7), "3–7 days"),
        else_="8+ days")
    rows = (db.session.query(MaintenanceRequest.priority,age.label("age"),
                func.count(MaintenanceRequest.id).label("total"))
            .filter(MaintenanceRequest.status.in_(OPEN))
            .group_by(MaintenanceRequest.priority,age)
            .order_by(MaintenanceRequest.priority,age).all())
    return jsonify(
        points=[{"name":str(priority).title()+" · "+str(age_bucket),
                 "priority":priority,"age":age_bucket,"value":int(count)}
                for priority,age_bucket,count in rows],
        unit="tickets",
        method=("Open/assigned/in-progress/on-hold maintenance grouped in SQL "
                "by recorded priority and days since creation. "
                "These are aging categories, NOT contractually agreed SLA breaches."))
