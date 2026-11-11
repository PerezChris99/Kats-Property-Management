"""Database-enforced document tenant isolation under a non-owner SQL role."""
import os
import uuid
import pytest
from app.document_rls import trusted_worker_scope

@pytest.fixture(autouse=True)
def migrated_db_test_service_context():
    # Setup/verification SQL runs outside an HTTP request in this DISPOSABLE
    # database; normal request tests still install their real JWT actor scope.
    with trusted_worker_scope():
        yield

import psycopg
from app import create_app
from app.extensions import db
from app.models import User, Tenant
from app.extra_models import Document
from argon2 import PasswordHasher

def test_nonprivileged_document_role_is_default_deny_and_transaction_scoped():
    db_url=os.getenv("TEST_POSTGRES_URL","")
    rls_url=os.getenv("TEST_DOCUMENT_RLS_URL","")
    if not db_url or not rls_url:
        pytest.skip("Requires disposable migrated PostgreSQL and a restricted SQL test user")
    if "kats_ci" not in db_url or "kats_ci" not in rls_url:
        raise RuntimeError("Refusing to run RLS integration test outside kats_ci")
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":db_url,
                    "RATELIMIT_ENABLED":False})
    with app.app_context():
        owner=User(full_name="RLS owner",email="rls-"+uuid.uuid4().hex+"@kats.test",
                   role="OWNER",password_hash=PasswordHasher().hash("ValidPassword123!"))
        db.session.add(owner);db.session.flush()
        t1=Tenant(full_name="Row A",phone="+256700"+str(uuid.uuid4().int%1000000).zfill(6))
        t2=Tenant(full_name="Row B",phone="+256700"+str(uuid.uuid4().int%1000000).zfill(6))
        db.session.add_all([t1,t2]);db.session.flush()
        a=Document(owner_user_id=owner.id,tenant_id=t1.id,category="LEASE",
                   filename="lease.pdf",object_key="rls-private/"+uuid.uuid4().hex,
                   mime_type="application/pdf",size_bytes=100)
        b=Document(owner_user_id=owner.id,tenant_id=t2.id,category="ID",
                   filename="id.pdf",object_key="rls-private/"+uuid.uuid4().hex,
                   mime_type="application/pdf",size_bytes=100)
        db.session.add_all([a,b]);db.session.commit()
        ids=(a.id,b.id)
        own_tenant=t1.id
    with psycopg.connect(rls_url,autocommit=True) as conn:
        # Setting no role must never expose either document.
        assert conn.execute("SELECT count(*) FROM documents WHERE id = ANY(%s)",(list(ids),)).fetchone()[0]==0
        with conn.transaction():
            conn.execute("SELECT set_config('kats.actor_role','TENANT',true)")
            conn.execute("SELECT set_config('kats.actor_tenant_id',%s,true)",(own_tenant,))
            records=conn.execute("SELECT id FROM documents WHERE id = ANY(%s)",(list(ids),)).fetchall()
            assert [r[0] for r in records]==[ids[0]]
            # A tenant must never read another tenant's private ID.
            assert conn.execute("SELECT count(*) FROM documents WHERE id=%s",(ids[1],)).fetchone()[0]==0
        assert conn.execute("SELECT count(*) FROM documents WHERE id = ANY(%s)",(list(ids),)).fetchone()[0]==0
        with conn.transaction():
            conn.execute("SELECT set_config('kats.actor_role','OWNER',true)")
            assert conn.execute("SELECT count(*) FROM documents WHERE id = ANY(%s)",(list(ids),)).fetchone()[0]==2
        assert conn.execute("SELECT count(*) FROM documents WHERE id = ANY(%s)",(list(ids),)).fetchone()[0]==0
