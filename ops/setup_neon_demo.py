"""Initialize the isolated katsproperty Neon PostgreSQL demo safely, once.

Run from an operator-controlled environment with a distinct migration DB role.
Never called during Vercel deploy or HTTP request; never use live customer data.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
BACK = ROOT / "backend"
sys.path.insert(0, str(BACK))
sys.path.insert(0, str(ROOT / "ops"))


def verify_environment():
    from seed_demo_preview import assert_public_neon_demo_database
    if os.getenv("KATS_NEON_SETUP") != "1":
        raise RuntimeError("KATS_NEON_SETUP=1 required; refusing DB initialization")
    assert_public_neon_demo_database()
    if os.getenv("KATS_TASK_MODE", "inline") != "inline":
        raise RuntimeError("Redis-free demo setup requires KATS_TASK_MODE=inline")
    if os.getenv("KATS_PREVIEW_MODE") == "1":
        raise RuntimeError("External Neon database cannot use local KATS_PREVIEW_MODE")


def assert_safe_target(connection):
    """Require empty/migrated demo-only schema; never touch a customer DB."""
    name = connection.execute(text("SELECT current_database()")).scalar_one()
    if name != "katsproperty":
        raise RuntimeError("Unexpected database; refusing schema migration")
    tables = set(connection.execute(text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """)).scalars())
    if tables and "alembic_version" not in tables:
        raise RuntimeError("Nonempty schema without Alembic history; refusing to guess")
    if "users" in tables:
        occupied = connection.execute(text("""
            SELECT EXISTS(SELECT 1 FROM users WHERE email NOT LIKE '%@demo.kats.invalid')
        """)).scalar_one()
        if occupied:
            raise RuntimeError("Non-demo account found; refusing migration/seed")


def main():
    verify_environment()
    from app import create_app
    from app.extensions import db
    from flask_migrate import upgrade
    from seed_demo_preview import seed, verify_existing
    from alembic.script import ScriptDirectory
    from alembic.config import Config as AlembicConfig

    app = create_app()
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            raise RuntimeError("PostgreSQL required")
        with db.engine.connect() as connection:
            assert_safe_target(connection)

        # Must execute the existing chain; NEVER db.create_all() or a partial
        # hand-built schema that omits RLS policies and accounting triggers.
        upgrade(directory=str(BACK / "migrations"))
        result = app.test_cli_runner().invoke(args=["seed-permissions"])
        if result.exit_code:
            raise RuntimeError("Role/route permission seeding failed")
        db.session.remove()
    seed(public_demo=True)
    with app.app_context():
        cfg = AlembicConfig()
        cfg.set_main_option("script_location", str(BACK / "migrations"))
        heads = set(ScriptDirectory.from_config(cfg).get_heads())
        with db.engine.connect() as connection:
            actual = set(connection.execute(text(
                "SELECT version_num FROM alembic_version"
            )).scalars())
            if heads != actual:
                raise RuntimeError("Alembic head mismatch after setup")
            table_count = connection.execute(text("""
                SELECT count(*) FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)).scalar_one()
        if not verify_existing():
            raise RuntimeError("Demo users, leases and invoices failed validation")
        print(f"[PASS] Migrated PostgreSQL to {', '.join(sorted(heads))}; "
              f"{table_count} public tables; 1 fictional owner + 30 tenants. "
              "No real tenants, money transfers or SMTP invitations were created.",
              flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Never log DSNs/passwords/exception values from external drivers.
        print("[BLOCKED] Neon demo initialization failed (" +
              type(error).__name__ + "). Inspect protected operator logs.",
              file=sys.stderr)
        raise SystemExit(1)
