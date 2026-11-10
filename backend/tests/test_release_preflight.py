"""Safe release preflight contract: no write actions, no false approval."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("release_gate", ROOT / "backend" / "app" / "release_preflight.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_preflight_never_runs_outside_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    assert gate.main() == 2


def test_preflight_fails_closed_without_production_secrets(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    for name in ("DATABASE_URL", "REDIS_URL", "SECRET_KEY", "JWT_SECRET_KEY", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    assert gate.main() == 2


def test_preflight_is_read_only_and_explicit_about_pending_acceptance():
    source = (ROOT / "backend" / "app" / "release_preflight.py").read_text(encoding="utf-8")
    assert "check_schema_and_role" in source
    assert "relforcerowsecurity" in source
    assert "rolbypassrls" in source
    assert "get_heads()" in source
    assert "Redis.from_url" in source
    assert "[NOT APPROVED]" in source
    assert "drop_all()" not in source
    assert "db upgrade" not in source
    assert "db.session.commit()" not in source
