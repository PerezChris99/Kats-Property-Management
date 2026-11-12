"""Production release gate requires verified MFA for active privileged accounts."""
import pytest
from sqlalchemy import text
from app.extensions import db
from app.release_preflight import check_privileged_mfa
from conftest import create_user


def test_release_requires_owner_and_privileged_mfa(app):
    with pytest.raises(RuntimeError, match="active owner"):
        with db.engine.connect() as connection:
            check_privileged_mfa(connection)
    owner=create_user("single-owner@example.invalid","OWNER")
    with pytest.raises(RuntimeError, match="enroll MFA"):
        with db.engine.connect() as connection:
            check_privileged_mfa(connection)

    owner.mfa_secret_encrypted="encrypted-test-value-is-not-real-secret"
    owner.mfa_enabled=True
    db.session.commit()
    with db.engine.connect() as connection:
        check_privileged_mfa(connection)

    manager=create_user("manager@example.invalid","MANAGER")
    with pytest.raises(RuntimeError, match="enroll MFA"):
        with db.engine.connect() as connection:
            check_privileged_mfa(connection)
    manager.is_active=False
    db.session.commit()
    with db.engine.connect() as connection:
        check_privileged_mfa(connection)

    accountant=create_user("accountant@example.invalid","ACCOUNTANT")
    accountant.mfa_secret_encrypted="encrypted-test-value-is-not-real-secret"
    accountant.mfa_enabled=True
    db.session.commit()
    with db.engine.connect() as connection:
        check_privileged_mfa(connection)
