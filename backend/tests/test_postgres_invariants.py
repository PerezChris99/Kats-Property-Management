"""PostgreSQL-only integration checks against migrated schema.

Run after "flask db upgrade" on the disposable CI database; never use
production/real customer data. Default local SQLite unit tests skip these.
"""
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import pytest
from app.document_rls import trusted_worker_scope

@pytest.fixture(autouse=True)
def migrated_db_test_service_context():
    # Setup/verification SQL runs outside an HTTP request in this DISPOSABLE
    # database; normal request tests still install their real JWT actor scope.
    with trusted_worker_scope():
        yield

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from argon2 import PasswordHasher
from app import create_app
from app.extensions import db
from app.models import (User, Property, Room, Tenant, Lease, Invoice, Payment,
                        LedgerEntry, AuditLog)
from conftest import auth_client, csrf

def postgres_application():
    url=os.getenv("TEST_POSTGRES_URL","")
    if not url:
        pytest.skip("Requires disposable migrated PostgreSQL test database")
    if not url.startswith("postgresql") or "kats_ci" not in url:
        raise RuntimeError("Refusing to run PostgreSQL integration tests outside kats_ci")
    return create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":url,
                       "RATELIMIT_ENABLED":False})

def seed_user(email,role):
    user=User(full_name=email,email=email,role=role,
              password_hash=PasswordHasher().hash("VerifiedTestPassword123!"))
    db.session.add(user)
    db.session.flush()
    return user

def test_postgres_append_only_audit_and_ledger_constraint():
    app=postgres_application()
    with app.app_context():
        actor=seed_user("pg-audit-"+uuid.uuid4().hex[:8]+"@kats.test","OWNER")
        log=AuditLog(actor_id=actor.id,action="TEST_EVENT",target_type="user",
                     target_id=actor.id,details={"purpose":"db gate"})
        db.session.add(log);db.session.commit()
        # Triggers installed by 0010_append_only reject SQL-level modifications.
        with pytest.raises(DBAPIError):
            db.session.execute(text("UPDATE audit_logs SET action='TAMPERED' WHERE id=:id"),
                               {"id":log.id})
            db.session.commit()
        db.session.rollback()
        with pytest.raises(DBAPIError):
            db.session.execute(text("DELETE FROM audit_logs WHERE id=:id"),{"id":log.id})
            db.session.commit()
        db.session.rollback()
        assert db.session.get(AuditLog,log.id).action=="TEST_EVENT"

def test_postgres_parallel_approval_posts_ledger_once():
    app=postgres_application()
    with app.app_context():
        maker=seed_user("pg-maker-"+uuid.uuid4().hex[:8]+"@kats.test","OWNER")
        checker=seed_user("pg-checker-"+uuid.uuid4().hex[:8]+"@kats.test","ACCOUNTANT")
        p=Property(name="Parallel",address="Kampala",district="Kampala")
        db.session.add(p);db.session.flush()
        room=Room(property_id=p.id,number="T-1",rent_ugx=200000,status="OCCUPIED")
        tenant=Tenant(full_name="Parallel Tenant",phone="+256700100998")
        db.session.add_all([room,tenant]);db.session.flush()
        lease=Lease(room_id=room.id,tenant_id=tenant.id,
                    start_date=date(2026,1,1),end_date=date(2027,1,1),
                    rent_ugx=200000)
        db.session.add(lease);db.session.flush()
        invoice=Invoice(invoice_number="PG-TEST-"+uuid.uuid4().hex[:16],
                        lease_id=lease.id,tenant_id=tenant.id,
                        period_start=date(2026,11,1),period_end=date(2026,11,30),
                        due_date=date(2026,11,9),total_ugx=200000)
        db.session.add(invoice);db.session.flush()
        payment=Payment(invoice_id=invoice.id,amount_ugx=80000,method="CASH",
                        status="PENDING_REVIEW",idempotency_key="pg-"+uuid.uuid4().hex,
                        created_by=maker.id)
        db.session.add(payment);db.session.commit()
        payid=payment.id; checkid=checker.id; invoiceid=invoice.id
    gate=threading.Barrier(2)
    def do_approve():
        with app.app_context():
            checker=db.session.get(User,checkid)
            client=auth_client(app,checker)
            gate.wait(timeout=12)
            result=client.post("/api/v1/payments/"+payid+"/approve",headers=csrf(client))
            return result.status_code,result.json
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(do_approve) for _ in range(2)]
        results=[job.result(timeout=20) for job in futures]
    assert all(code==200 for code,_ in results),results
    with app.app_context():
        assert db.session.get(Invoice,invoiceid).paid_ugx==80000
        assert db.session.query(LedgerEntry).filter_by(payment_id=payid,
              event="PAYMENT_RECEIVED").count()==1
        assert db.session.get(Payment,payid).status=="RECONCILED"
