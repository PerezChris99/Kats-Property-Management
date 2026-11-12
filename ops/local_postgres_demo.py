"""Isolated, Docker-free KATS PostgreSQL demo for a LOCAL Windows PG server.

Creates only kats_demo + dedicated non-superuser roles. Existing databases
are never dropped, migrated, or modified. Admin password is never persisted.
"""
from __future__ import annotations
import argparse
import getpass
import os
from pathlib import Path
import secrets
import subprocess
import sys
from urllib.parse import quote
import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/".env.pg-demo"
NAME="kats_demo"
OWNER="kats_demo_owner"
RUNTIME="kats_demo_runtime"
SIGNATURE="kats-local-postgres-demo-v1"
EXPECTED={"users":31,"tenants":30,"properties":3,"buildings":3,"floors":9,
          "rooms":33,"leases":30,"invoices":60,"invoice_lines":60}

def load():
    if not CONFIG.exists():
        raise RuntimeError("Missing ignored .env.pg-demo: run PostgreSQL demo setup")
    out={}
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            k,sep,v=line.partition("=")
            if not sep or not k or not v: raise RuntimeError("Invalid .env.pg-demo")
            out[k]=v
    keys=("KATS_DEMO_INSTANCE","KATS_PG_DEMO_PORT","OWNER_PASSWORD",
          "RUNTIME_PASSWORD","SECRET_KEY","JWT_SECRET_KEY")
    if any(not out.get(k) for k in keys):
        raise RuntimeError("Incomplete PostgreSQL demo configuration")
    if (not out["KATS_PG_DEMO_PORT"].isdecimal() or
        not 1024<=int(out["KATS_PG_DEMO_PORT"])<=65535 or
        len(out["KATS_DEMO_INSTANCE"])!=32 or
        min(len(out["OWNER_PASSWORD"]),len(out["RUNTIME_PASSWORD"]))<32):
        raise RuntimeError("Unsafe demo credentials or localhost port")
    return out

def initialize():
    if CONFIG.exists(): return load()
    port=os.getenv("KATS_PG_DEMO_PORT","5432")
    if not port.isdecimal() or not 1024<=int(port)<=65535:
        raise RuntimeError("Local PG port must be 1024–65535")
    values={"KATS_DEMO_INSTANCE":secrets.token_hex(16),
            "KATS_PG_DEMO_PORT":port,"OWNER_PASSWORD":secrets.token_hex(32),
            "RUNTIME_PASSWORD":secrets.token_hex(32),
            "SECRET_KEY":secrets.token_hex(32),"JWT_SECRET_KEY":secrets.token_hex(32)}
    fd=os.open(CONFIG,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as handle:
        handle.write("# Isolated local demo only. NEVER COMMIT.\n")
        for k,v in values.items():handle.write(f"{k}={v}\n")
    return values

def conninfo(values,role,database=NAME):
    return dict(host="127.0.0.1",port=int(values["KATS_PG_DEMO_PORT"]),
                dbname=database,user=role,
                password=values["OWNER_PASSWORD" if role==OWNER else "RUNTIME_PASSWORD"],
                connect_timeout=5)

def uri(values,role):
    return ("postgresql+psycopg://"+role+":"+
            quote(values["OWNER_PASSWORD" if role==OWNER else "RUNTIME_PASSWORD"],safe="")+
            "@127.0.0.1:"+values["KATS_PG_DEMO_PORT"]+"/"+NAME)

def marker(values,role=OWNER):
    with psycopg.connect(**conninfo(values,role)) as conn:
        row=conn.execute("SELECT instance_id,signature FROM public.kats_demo_marker").fetchone()
        if row!=(values["KATS_DEMO_INSTANCE"],SIGNATURE):
            raise RuntimeError("DB marker does not match this local demo. Refusing operations.")
    return True

def admin_bootstrap(values):
    admin=os.getenv("KATS_PG_ADMIN_USER","postgres")
    if admin in (OWNER,RUNTIME) or not admin: raise RuntimeError("PG admin account required")
    pwd=os.getenv("KATS_PG_ADMIN_PASSWORD") or getpass.getpass(
        f"Local PostgreSQL admin password ({admin}, 127.0.0.1:{values['KATS_PG_DEMO_PORT']}): ")
    if not pwd: raise RuntimeError("PostgreSQL admin password is required")
    try:
        with psycopg.connect(host="127.0.0.1",port=int(values["KATS_PG_DEMO_PORT"]),
                             dbname="postgres",user=admin,password=pwd,
                             connect_timeout=5,autocommit=True) as conn:
            if not conn.execute(
                "SELECT rolsuper OR rolcreaterole FROM pg_roles WHERE rolname=current_user"
            ).fetchone()[0]:
                raise RuntimeError("Existing local admin lacks PostgreSQL role creation privileges")
            for role in (OWNER,RUNTIME):
                exists=conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s",(role,)).fetchone()
                if exists:
                    try:
                        with psycopg.connect(**conninfo(values,role,database="postgres")):
                            pass
                    except psycopg.Error as e:
                        raise RuntimeError("Existing role "+role+" has other credentials; refusing overwrite") from e
                else:
                    password=values["OWNER_PASSWORD" if role==OWNER else "RUNTIME_PASSWORD"]
                    conn.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}").format(
                        sql.Identifier(role),sql.Literal(password)))
            row=conn.execute("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s",(NAME,)).fetchone()
            if row:
                if row[0]!=OWNER:
                    raise RuntimeError("Existing kats_demo has an unrelated owner; refusing changes")
            else:
                conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(NAME),sql.Identifier(OWNER)))
            conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(NAME),sql.Identifier(RUNTIME)))
    finally:
        del pwd
    with psycopg.connect(**conninfo(values,OWNER)) as conn:
        if conn.execute("SELECT to_regclass('public.kats_demo_marker')").fetchone()[0]:
            row=conn.execute("SELECT instance_id,signature FROM public.kats_demo_marker").fetchone()
            if row!=(values["KATS_DEMO_INSTANCE"],SIGNATURE):
                raise RuntimeError("Existing demo database marker mismatch")
        else:
            count=conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone()[0]
            if count: raise RuntimeError("Existing kats_demo has unrelated tables; refusing changes")
            conn.execute("CREATE TABLE public.kats_demo_marker (instance_id varchar(32) PRIMARY KEY, signature varchar(64) NOT NULL)")
            conn.execute("INSERT INTO public.kats_demo_marker VALUES (%s,%s)",
                         (values["KATS_DEMO_INSTANCE"],SIGNATURE))
            conn.execute("REVOKE ALL ON public.kats_demo_marker FROM PUBLIC")
            conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(RUNTIME)))
            conn.execute(sql.SQL("GRANT SELECT ON public.kats_demo_marker TO {}").format(sql.Identifier(RUNTIME)))
    marker(values)

def environ(values,role):
    out=os.environ.copy()
    out.update(APP_ENV="development",KATS_LOCAL_PG_DEMO="1",
               KATS_LOCAL_PG_INSTANCE=values["KATS_DEMO_INSTANCE"],
               KATS_LOCAL_PG_PORT=values["KATS_PG_DEMO_PORT"],KATS_SEED_DEMO="1",
               KATS_PREVIEW_MODE="0",DATABASE_URL=uri(values,role),
               SECRET_KEY=values["SECRET_KEY"],JWT_SECRET_KEY=values["JWT_SECRET_KEY"],
               CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:5173",
               COOKIE_SECURE="false",PUBLIC_REGISTRATION_ENABLED="false",
               REDIS_URL="memory://",RATELIMIT_STORAGE_URI="memory://",
               CELERY_BROKER_URL="memory://",CELERY_RESULT_BACKEND="cache+memory://",
               CELERY_TASK_ALWAYS_EAGER="true",TRUST_PROXY_HEADERS="false",
               MTN_MOMO_ENABLED="false",AIRTEL_MONEY_ENABLED="false",
               EFRIS_ENABLED="false",EMAIL_PROVIDER_ENABLED="false",SMS_PROVIDER_ENABLED="false")
    for name in ("KATS_PG_ADMIN_PASSWORD","S3_BUCKET","S3_ENDPOINT_URL",
                 "AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY","SMTP_HOST",
                 "SMTP_PASSWORD","MTN_MOMO_API_KEY","AIRTEL_MONEY_CLIENT_SECRET"):
        out.pop(name,None)
    return out

def run(values,role,args,cwd=ROOT):
    result=subprocess.run([sys.executable,*args],cwd=cwd,env=environ(values,role),check=False)
    if result.returncode:
        raise RuntimeError(f"PostgreSQL demo step failed with exit code {result.returncode}: {args[0]}")

def grants(values):
    with psycopg.connect(**conninfo(values,OWNER)) as conn:
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(RUNTIME)))
        conn.execute(sql.SQL("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(RUNTIME)))
        conn.execute(sql.SQL("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(sql.Identifier(RUNTIME)))
        conn.execute(sql.SQL("REVOKE ALL ON public.kats_demo_marker FROM {}").format(sql.Identifier(RUNTIME)))
        conn.execute(sql.SQL("GRANT SELECT ON public.kats_demo_marker TO {}").format(sql.Identifier(RUNTIME)))

def verify(values):
    marker(values)
    with psycopg.connect(**conninfo(values,OWNER)) as conn:
        conn.execute("SELECT set_config('kats.actor_role','SERVICE',true)")
        counts={}
        for table,expected in EXPECTED.items():
            actual=conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
            counts[table]=actual
            if actual!=expected:
                raise RuntimeError(f"Seed {table} expected {expected}, got {actual}")
        for table,field,wanted in (("users","role",30),("leases","status",30),("rooms","status",30)):
            value={"users":"TENANT","leases":"ACTIVE","rooms":"OCCUPIED"}[table]
            actual=conn.execute(sql.SQL("SELECT count(*) FROM {} WHERE {}=%s").format(
                sql.Identifier(table),sql.Identifier(field)),(value,)).fetchone()[0]
            if actual!=wanted:raise RuntimeError("Linked demo statuses inconsistent in "+table)
        if conn.execute("SELECT count(*) FROM invoices i LEFT JOIN tenants t ON t.id=i.tenant_id WHERE t.id IS NULL").fetchone()[0]:
            raise RuntimeError("Orphaned invoice found")
        if conn.execute("SELECT count(*) FROM tenants t LEFT JOIN users u ON u.id=t.user_id WHERE u.id IS NULL").fetchone()[0]:
            raise RuntimeError("Orphaned tenant found")
        # Resolve the migration head dynamically; otherwise every new Alembic
        # revision breaks an otherwise healthy local PostgreSQL demo.
        from alembic.config import Config as AlembicConfig
        from alembic.script import ScriptDirectory
        config = AlembicConfig()
        config.set_main_option("script_location", str(ROOT / "backend" / "migrations"))
        expected_heads = set(ScriptDirectory.from_config(config).get_heads())
        actual_heads = {row[0] for row in conn.execute("SELECT version_num FROM alembic_version")}
        if not expected_heads or actual_heads != expected_heads:
            raise RuntimeError("PostgreSQL migrations are not at latest head")
        tables=("documents","tenants","leases","invoices","payments","maintenance_requests","notifications")
        rows=conn.execute("SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname=ANY(%s) AND relnamespace='public'::regnamespace",(list(tables),)).fetchall()
        if len(rows)!=7 or any(not(r[1] and r[2]) for r in rows):
            raise RuntimeError("Missing FORCE RLS on core private table")
        user_id,tenant_id=conn.execute(
            "SELECT u.id,t.id FROM users u JOIN tenants t ON t.user_id=u.id "
            "WHERE u.email='tenant01@demo.kats.invalid'").fetchone()
    with psycopg.connect(**conninfo(values,RUNTIME)) as conn:
        flags=conn.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone()
        if any(flags):raise RuntimeError("Runtime role has unsafe PostgreSQL privileges")
        for table in ("tenants","leases","invoices","payments","maintenance_requests"):
            if conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]:
                raise RuntimeError("Unscoped runtime can read "+table)
        conn.commit()
        with conn.transaction():
            conn.execute("SELECT set_config('kats.actor_role','TENANT',true)")
            conn.execute("SELECT set_config('kats.actor_user_id',%s,true)",(user_id,))
            conn.execute("SELECT set_config('kats.actor_tenant_id',%s,true)",(tenant_id,))
            if conn.execute("SELECT count(*) FROM invoices").fetchone()[0]!=2:
                raise RuntimeError("Tenant RLS must show only its two invoices")
    run(values,RUNTIME,[str(ROOT/"ops"/"verify_pg_demo_http.py")])
    print("[PASS] Local PostgreSQL / RLS / all 31 demo roles and links verified")
    print("[DATA] "+", ".join(f"{k}={v}" for k,v in counts.items()))

def setup():
    values=initialize()
    admin_bootstrap(values)
    run(values,OWNER,["-m","flask","--app","wsgi","db","upgrade"],ROOT/"backend")
    run(values,OWNER,["-m","flask","--app","wsgi","seed-permissions"],ROOT/"backend")
    run(values,OWNER,[str(ROOT/"ops"/"seed_demo_preview.py"),"--postgres"])
    grants(values)
    verify(values)
    print("[READY] Choose VS Code: KATS PostgreSQL demo start (31 accounts)")

def prepare():
    """Initialize a new synthetic PG demo ONCE; existing instances are read-only.

    Never rerun migrations, permissions, seed or grants on ordinary startup.
    An interrupted initial database creation may reenter the guarded
    bootstrap, but unrelated databases and mismatched markers fail closed.
    """
    if not CONFIG.exists():
        setup()
        return
    values=load()
    try:
        marker(values,OWNER)
    except (psycopg.OperationalError, psycopg.errors.UndefinedTable):
        print("[setup] Incomplete localhost demo bootstrap; checking safe recovery...",flush=True)
        setup()
        return
    marker(values,RUNTIME)
    print("[READY] Reusing existing kats_demo PostgreSQL; no migrations or seeding.",flush=True)


def upgrade_schema():
    """Explicit opt-in code upgrades; preserve ALL existing demo records."""
    values=load()
    marker(values,OWNER)
    marker(values,RUNTIME)
    run(values,OWNER,["-m","flask","--app","wsgi","db","upgrade"],ROOT/"backend")
    run(values,OWNER,["-m","flask","--app","wsgi","seed-permissions"],ROOT/"backend")
    grants(values)
    marker(values,RUNTIME)
    print("[READY] Local PostgreSQL schema and permissions upgraded; no demo seeding.",flush=True)


def main():
    parser=argparse.ArgumentParser(description="Local PostgreSQL synthetic demo, never production")
    parser.add_argument("action",choices=("setup","prepare","upgrade","verify","check","serve"))
    action=parser.parse_args().action
    try:
        if action=="setup":setup()
        elif action=="prepare":prepare()
        elif action=="upgrade":upgrade_schema()
        else:
            values=load()
            marker(values,RUNTIME)
            if action=="verify":verify(values)
            if action=="serve":
                print("[postgres-demo] Starting Flask on 127.0.0.1:8000")
                result=subprocess.run([sys.executable,"-m","flask","--app","wsgi",
                                       "run","--no-reload","--host","127.0.0.1","--port","8000"],
                                      cwd=ROOT/"backend",env=environ(values,RUNTIME))
                return result.returncode
        return 0
    except (RuntimeError,psycopg.Error,OSError) as exc:
        print("[ERROR] Local PG demo: "+str(exc),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
