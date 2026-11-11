"""Read-only production release gate. It does not migrate or change records.

Run *inside* the approved deployment with production environment and the
restricted API database role. PASS does not imply regulatory/provider approval.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

BACK = Path(__file__).resolve().parents[1]


def check_schema_and_role(connection, heads):
    """Fail closed when migrations/RLS or restricted-role constraints differ."""
    from sqlalchemy import text
    actual = {r[0] for r in connection.execute(text("SELECT version_num FROM alembic_version"))}
    if not actual or actual != set(heads):
        raise RuntimeError("Database migrations are not at application head")
    role = connection.execute(text(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
    )).one()
    if role.rolsuper or role.rolbypassrls:
        raise RuntimeError("The runtime database role must not be superuser or BYPASSRLS")
    required = ("documents", "tenants", "leases", "invoices",
                "payments", "maintenance_requests", "notifications")
    policies = connection.execute(text(
        "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, "
        "EXISTS(SELECT 1 FROM pg_policies p WHERE p.schemaname=current_schema() "
        "AND p.tablename=c.relname AND p.policyname= "
        "CASE WHEN c.relname='documents' THEN 'kats_document_scope' "
        "ELSE 'kats_runtime_scope' END) "
        "FROM pg_class c WHERE c.relnamespace = current_schema()::regnamespace "
        "AND c.relname = ANY(:tables)"
    ), {"tables":list(required)}).all()
    if (len(policies)!=len(required) or
        {row.relname for row in policies}!=set(required) or
        any(not (row.relrowsecurity and row.relforcerowsecurity and row[3])
            for row in policies)):
        raise RuntimeError("Document and tenancy/finance tables must have FORCE RLS policies")


def main():
    if os.getenv("APP_ENV") != "production":
        print("[BLOCKED] Preflight is for APP_ENV=production only.", file=sys.stderr)
        return 2
    try:
        from app.config import validate_production_config
        validate_production_config()
    except (RuntimeError, ValueError) as exc:
        # Config-validation errors contain key names, never environment values.
        print("[BLOCKED] Production config: " + str(exc), file=sys.stderr)
        return 2
    try:
        from alembic.config import Config as AlembicConfig
        from alembic.script import ScriptDirectory
        from sqlalchemy import text
        from redis import Redis
        from app import create_app
        from app.extensions import db
        cfg = AlembicConfig()
        cfg.set_main_option("script_location", str(BACK / "migrations"))
        heads = ScriptDirectory.from_config(cfg).get_heads()
        app = create_app()
        with app.app_context():
            if db.engine.dialect.name != "postgresql":
                raise RuntimeError("Production requires PostgreSQL")
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1")).scalar_one()
                check_schema_and_role(conn, heads)
        with Redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=4,
                            socket_timeout=4) as redis:
            if not redis.ping():
                raise RuntimeError("Redis is not responding")
    except Exception as exc:
        # Never print DSNs, passwords, connection arguments or SQL values.
        print("[BLOCKED] Runtime readiness failed (" + type(exc).__name__ +
              "). Check private service logs.", file=sys.stderr)
        return 3
    print("[PASS] Production settings, schema revision, restricted DB role, "
          "document/tenancy/finance RLS and Redis connectivity.")
    print("[NOT APPROVED] Operator must still sign off on TLS, MFA, backup/restore, "
          "tenancy workflow, providers, security and legal acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
