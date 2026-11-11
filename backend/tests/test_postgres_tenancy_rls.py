"""PostgreSQL FORCE-RLS isolation of financial and tenancy rows.

Only uses the disposable kats_ci instance and a genuinely restricted SQL role.
The worker-scoped fixture builds data; direct psycopg reads test database policy,
independent of Flask's response filtering.
"""
import os
import uuid
from datetime import date
import psycopg
import pytest
from argon2 import PasswordHasher
from app import create_app
from app.document_rls import trusted_worker_scope
from app.extensions import db
from app.models import (User, Tenant, Property, Room, Lease, Invoice, Payment,
                        MaintenanceRequest, CaretakerAssignment)
from app.extra_models import Notification


def integration_urls():
    db_url=os.getenv("TEST_POSTGRES_URL","")
    rls_url=os.getenv("TEST_DOCUMENT_RLS_URL","")
    if not db_url or not rls_url:
        pytest.skip("Requires disposable migrated PostgreSQL kats_ci with restricted RLS user")
    if "kats_ci" not in db_url or "kats_ci" not in rls_url:
        raise RuntimeError("Refusing row security test outside disposable kats_ci")
    return db_url,rls_url


def test_core_financial_row_policies_default_deny_and_enforce_tenant_isolation():
    db_url,rls_url=integration_urls()
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":db_url,
                    "RATELIMIT_ENABLED":False})
    with trusted_worker_scope(),app.app_context():
        suffix=uuid.uuid4().hex[:12]
        users=[]
        for index in range(2):
            user=User(full_name=f"Isolated Tenant {index}",role="TENANT",
                      email=f"rls-tenant-{index}-{suffix}@kats.test",
                      password_hash=PasswordHasher().hash("TestPassword98765!"))
            db.session.add(user);users.append(user)
        caretaker=User(full_name="Test caretaker",role="CARETAKER",
                       email=f"rls-care-{suffix}@kats.test",
                       password_hash=PasswordHasher().hash("TestPassword98765!"))
        db.session.add(caretaker)
        prop=Property(name="RLStest "+suffix,address="Kampala demo",district="Kampala")
        db.session.add(prop);db.session.flush()
        tenant_rows=[];lease_rows=[];invoice_rows=[];payment_rows=[];repair_rows=[];notice_rows=[]
        for index,user in enumerate(users):
            tenant=Tenant(user_id=user.id,full_name=user.full_name,
                          phone=f"+256700{index:06d}")
            room=Room(property_id=prop.id,number=f"RLS-{index}-{suffix}",
                      status="OCCUPIED",rent_ugx=330000)
            db.session.add_all([tenant,room]);db.session.flush()
            lease=Lease(tenant_id=tenant.id,room_id=room.id,
                        start_date=date(2026,1,1),end_date=date(2027,12,31),
                        rent_ugx=330000)
            db.session.add(lease);db.session.flush()
            inv=Invoice(invoice_number=f"RLS-{index}-{suffix}",
                        lease_id=lease.id,tenant_id=tenant.id,
                        period_start=date(2026,11,1),period_end=date(2026,11,30),
                        due_date=date(2026,11,5),total_ugx=330000)
            db.session.add(inv);db.session.flush()
            pay=Payment(invoice_id=inv.id,amount_ugx=20000,method="CASH",
                        created_by=user.id,idempotency_key=f"rls-pay-{index}-{suffix}",
                        status="PENDING_REVIEW")
            repair=MaintenanceRequest(room_id=room.id,tenant_id=tenant.id,
                                      title="Demo test",description="Restricted")
            notice=Notification(user_id=user.id,channel="IN_APP",kind="NOTICE",
                                title="Tenant notice",body="Private",
                                status="PENDING",dedupe_key=f"rls-notice-{index}-{suffix}")
            db.session.add_all([pay,repair,notice]);db.session.flush()
            if index==0:
                db.session.add(CaretakerAssignment(room_id=room.id,
                                                   caretaker_user_id=caretaker.id))
            tenant_rows.append(tenant);lease_rows.append(lease);invoice_rows.append(inv)
            payment_rows.append(pay);repair_rows.append(repair);notice_rows.append(notice)
        db.session.commit()
        ids={
          "tenant":[r.id for r in tenant_rows],
          "lease":[r.id for r in lease_rows],
          "invoice":[r.id for r in invoice_rows],
          "payment":[r.id for r in payment_rows],
          "repair":[r.id for r in repair_rows],
          "notification":[r.id for r in notice_rows],
        }
        user_ids=[r.id for r in users];caretaker_id=caretaker.id
    # Exercise Flask's two-phase tenant scope lookup against actual FORCE RLS;
    # SQLite unit tests cannot detect an unscoped profile query on PostgreSQL.
    from conftest import auth_client, csrf
    with app.app_context():
        tenant_user=db.session.get(User,user_ids[0])
        api_client=auth_client(app,tenant_user)
        lease_response=api_client.get("/api/v1/tenant/lease")
        assert lease_response.status_code==200,lease_response.get_json(silent=True)
        assert lease_response.json["lease"]["id"]==ids["lease"][0]
        summary=api_client.get("/api/v1/tenant/dashboard")
        assert summary.status_code==200
        assert summary.json["invoices"]==1
        own_invoices=api_client.get("/api/v1/invoices")
        assert own_invoices.status_code==200
        assert [entry["id"] for entry in own_invoices.json["items"]]==[ids["invoice"][0]]
        created=api_client.post("/api/v1/maintenance",json={
            "room_id":lease_response.json["lease"]["room_id"],
            "title":"RLS integration repair","description":"RLS-verified tenant work order"
        },headers=csrf(api_client))
        assert created.status_code==201,created.get_json(silent=True)
    tables={"tenant":"tenants","lease":"leases","invoice":"invoices",
            "payment":"payments","repair":"maintenance_requests",
            "notification":"notifications"}
    with psycopg.connect(rls_url,autocommit=True) as conn:
        for kind,table in tables.items():
            # Neither an accidental missing GUC nor pooled connection reuse
            # may expose private rows to an unscoped runtime SQL role.
            assert conn.execute(f"SELECT count(*) FROM {table} WHERE id=ANY(%s)",
                                (ids[kind],)).fetchone()[0]==0,kind
        with conn.transaction():
            conn.execute("SELECT set_config('kats.actor_role','TENANT',true)")
            conn.execute("SELECT set_config('kats.actor_user_id',%s,true)",(user_ids[0],))
            conn.execute("SELECT set_config('kats.actor_tenant_id',%s,true)",
                         (ids["tenant"][0],))
            for kind,table in tables.items():
                actual=conn.execute(f"SELECT id FROM {table} WHERE id=ANY(%s)",
                                    (ids[kind],)).fetchall()
                assert [x[0] for x in actual]==[ids[kind][0]],kind
            # Tenant cannot rewrite their own personal identity under SQL RLS.
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():  # savepoint keeps outer read transaction healthy
                    conn.execute(
                        "UPDATE tenants SET full_name='Forbidden' WHERE id=%s",
                        (ids["tenant"][0],))
        # Session-scoped config must not survive transaction commit.
        assert conn.execute("SELECT count(*) FROM invoices WHERE id=ANY(%s)",
                            (ids["invoice"],)).fetchone()[0]==0
        with conn.transaction():
            conn.execute("SELECT set_config('kats.actor_role','CARETAKER',true)")
            conn.execute("SELECT set_config('kats.actor_user_id',%s,true)",
                         (caretaker_id,))
            for kind in ("lease","invoice","payment","repair"):
                rows=conn.execute(f"SELECT id FROM {tables[kind]} WHERE id=ANY(%s)",
                                  (ids[kind],)).fetchall()
                assert [r[0] for r in rows]==[ids[kind][0]],kind
            assert conn.execute("SELECT count(*) FROM tenants WHERE id=ANY(%s)",
                                (ids["tenant"],)).fetchone()[0]==0
        with conn.transaction():
            conn.execute("SELECT set_config('kats.actor_role','OWNER',true)")
            for kind,table in tables.items():
                assert conn.execute(f"SELECT count(*) FROM {table} WHERE id=ANY(%s)",
                                    (ids[kind],)).fetchone()[0] == (0 if kind=="notification" else 2),kind
