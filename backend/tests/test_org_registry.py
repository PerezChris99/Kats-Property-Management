"""Additive organization registry is internal and does not weaken existing access controls."""
import pytest
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Property
from app.organization_models import (
    Organization, OrganizationMembership, PropertyOrganization, LEGACY_ORGANIZATION_ID,
)
from conftest import create_user


def test_organization_registry_is_strict_and_not_public(app):
    owner = create_user("orgowner@example.invalid", "OWNER")
    organization = Organization(
        id=LEGACY_ORGANIZATION_ID,slug="kats-legacy",legal_name="KATS Legacy",
        kind="PROPERTY_OWNER", country_code="UG", status="ACTIVE")
    property_record = Property(name="Sample",address="Example road",district="Kampala")
    db.session.add_all([organization,property_record])
    db.session.flush()
    db.session.add(OrganizationMembership(
        organization_id=organization.id,user_id=owner.id,role="OWNER",active=True))
    db.session.add(PropertyOrganization(
        organization_id=organization.id,property_id=property_record.id))
    db.session.commit()
    assert db.session.query(PropertyOrganization).filter_by(property_id=property_record.id).count()==1
    assert db.session.query(OrganizationMembership).filter_by(user_id=owner.id).count()==1
    assert not any("/organizations" in rule.rule for rule in app.url_map.iter_rules())
    db.session.add(Organization(slug="bad",legal_name="Invalid",kind="UNSUPPORTED",country_code="UG",status="ACTIVE"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
