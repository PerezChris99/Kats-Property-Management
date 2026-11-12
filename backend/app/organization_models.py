"""Inactive, additive organization registry for a future multi-organization migration.

This registry does NOT enable independent customer signup or override existing
single-company API permissions. Organization scope is a separate release gate.
"""
from datetime import datetime, timezone
from .extensions import db
from .models import new_id

def now_utc():
    return datetime.now(timezone.utc)

LEGACY_ORGANIZATION_ID = "11111111-1111-4111-8111-111111111111"

class Organization(db.Model):
    __tablename__ = "organizations"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    legal_name = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(25), nullable=False, default="PROPERTY_OWNER")
    country_code = db.Column(db.String(2), nullable=False, default="UG")
    status = db.Column(db.String(20), nullable=False, default="ACTIVE")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    __table_args__ = (
        db.CheckConstraint("kind IN ('PROPERTY_OWNER','AGENCY','INSTITUTION')", name="ck_org_kind"),
        db.CheckConstraint("status IN ('ACTIVE','SUSPENDED')", name="ck_org_status"),
    )

class OrganizationMembership(db.Model):
    __tablename__ = "organization_memberships"
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", ondelete="RESTRICT"), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    role = db.Column(db.String(30), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    __table_args__ = (db.Index("ix_org_memberships_user", "user_id", "active"),)

class PropertyOrganization(db.Model):
    __tablename__ = "property_organizations"
    property_id = db.Column(db.String(36), db.ForeignKey("properties.id", ondelete="RESTRICT"), primary_key=True)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
