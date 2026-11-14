"""Real migrated PostgreSQL enforces general-ledger balance and immutability.

Only runs against the disposable kats_ci database, not customer data.
"""
from datetime import date
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.document_rls import trusted_worker_scope
from app.extensions import db
from app.finance.gl_models import GLEvent, GLLine
from app.finance.ledger import post_event
from test_postgres_invariants import postgres_application


def test_postgres_balanced_gl_and_append_only_guards():
    app = postgres_application()
    with app.app_context(), trusted_worker_scope():
        key = "pg:balanced:" + uuid.uuid4().hex
        assert post_event(key, "RECEIPT", date(2026, 11, 1),
                          [("CASH_CLEARING", 15000, 0),
                           ("RENT_RECEIVABLE", 0, 15000)])
        db.session.commit()
        event = db.session.query(GLEvent).filter_by(event_key=key).one()
        line = db.session.query(GLLine).filter_by(event_id=event.id).first()
        assert line is not None
        with pytest.raises(DBAPIError):
            db.session.execute(text(
                "UPDATE gl_lines SET debit_ugx=12345 WHERE id=:id"), {"id":line.id})
            db.session.commit()
        db.session.rollback()
        with pytest.raises(DBAPIError):
            db.session.execute(text(
                "DELETE FROM gl_events WHERE id=:id"), {"id":event.id})
            db.session.commit()
        db.session.rollback()
        assert db.session.query(GLLine).filter_by(event_id=event.id).count() == 2


def test_postgres_deferred_balancing_refuses_dangling_event():
    app = postgres_application()
    with app.app_context(), trusted_worker_scope():
        bad = GLEvent(event_key="pg:dangling:"+uuid.uuid4().hex,
                      kind="TEST", posted_on=date(2026, 11, 1),
                      fingerprint="0"*64)
        db.session.add(bad)
        with pytest.raises(DBAPIError):
            db.session.commit()
        db.session.rollback()
