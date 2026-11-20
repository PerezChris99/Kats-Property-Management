"""Redis-free limits: registration, hashing, strict PostgreSQL and schema contract."""
from pathlib import Path
import hashlib
import pytest
from limits.storage import storage_from_string
from app.postgres_rate_limit import PostgresRateLimitStorage


def test_postgres_storage_is_registered_by_limits_and_never_uses_plain_ip_keys():
    store=storage_from_string("katsdb://")
    assert isinstance(store, PostgresRateLimitStorage)
    key="LIMITER/10.14.25.36/auth/login"
    assert store._key(key) == hashlib.sha256(key.encode()).hexdigest()
    assert "10.14.25.36" not in store._key(key)
    with pytest.raises(ValueError):
        storage_from_string("katsdb://wrong-endpoint")


def test_rate_limits_fail_closed_on_sqlite_development(app):
    with app.app_context():
        store=storage_from_string("katsdb://")
        with pytest.raises(RuntimeError, match="requires migrated PostgreSQL"):
            store.check()
        with pytest.raises(RuntimeError, match="requires migrated PostgreSQL"):
            store.incr("auth-login", 60)
        with pytest.raises(RuntimeError, match="requires migrated PostgreSQL"):
            store.get("auth-login")


def test_rate_limit_migration_is_linked_to_full_schema_and_does_not_remove_rls():
    root=Path(__file__).resolve().parents[2]
    migration=(root/"backend/migrations/versions/0036_postgres_rate_limits.py").read_text()
    assert 'down_revision = "0035_bank_statement_guard"' in migration
    assert "op.create_table(" in migration
    assert '"rate_limit_counters"' in migration
    assert 'expires_at' in migration
    model=(root/"backend/app/rate_limit_models.py").read_text()
    assert 'key_digest' in model and 'db.CheckConstraint' in model
    store=(root/"backend/app/postgres_rate_limit.py").read_text()
    assert "ON CONFLICT (key_digest) DO UPDATE" in store
    assert "RETURNING hits" in store
    assert "rate_limit_counters.expires_at <= now()" in store
    assert "with self._engine().begin()" in store
    assert "in_memory_fallback" not in store


def test_redis_free_operator_jobs_fail_closed_without_postgres(app, monkeypatch):
    monkeypatch.setenv("KATS_TASK_MODE", "inline")
    runner=app.test_cli_runner()
    scheduled=runner.invoke(args=["run-scheduled","rent-reminders"])
    assert scheduled.exit_code != 0
    assert "PostgreSQL" in scheduled.output
    prune=runner.invoke(args=["prune-rate-limits"])
    assert prune.exit_code != 0
    assert "PostgreSQL" in prune.output


def test_guarded_neon_demo_never_auto_creates_business_tables(monkeypatch):
    import importlib.util
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location("neon_setup",root/"ops/setup_neon_demo.py")
    script=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    monkeypatch.delenv("KATS_NEON_SETUP",raising=False)
    with pytest.raises(RuntimeError,match="KATS_NEON_SETUP"):
        script.verify_environment()
