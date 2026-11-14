"""Real migrated PostgreSQL enforces general-ledger balance and immutability.

Only runs against the disposable kats_ci database, not customer data.
"""
from datetime import date
import os
import uuid
import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.document_rls import trusted_worker_scope
from app.extensions import db
from app.finance.gl_models import GLEvent, GLLine
from app.finance.ledger import period_lock, post_event
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


def test_postgres_close_and_posting_share_one_cross_month_lock():
    """A newer-month close must block an older-month posting until it commits.

    Check the actual advisory key from a second independent PostgreSQL session,
    not an in-process mock. Both months use the same company-wide lock.
    """
    app = postgres_application()
    url = os.environ["TEST_POSTGRES_URL"].replace("+psycopg", "")
    with app.app_context(), trusted_worker_scope():
        period_lock("2025-04")
        with psycopg.connect(url, connect_timeout=5) as another:
            available = another.execute(
                "SELECT pg_try_advisory_xact_lock(hashtext(%s))",
                ("kats:gl:company",)).fetchone()[0]
            assert available is False
        db.session.rollback()
        # Once the original transaction ends, a different month can acquire
        # the exact same lock. This must not leave a persistent DB lock.
        with psycopg.connect(url, connect_timeout=5) as another:
            available = another.execute(
                "SELECT pg_try_advisory_xact_lock(hashtext(%s))",
                ("kats:gl:company",)).fetchone()[0]
            assert available is True
