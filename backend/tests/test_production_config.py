import pytest
from app.config import validate_production_config

def configure(monkeypatch):
    monkeypatch.setenv("APP_ENV","production")
    monkeypatch.setenv("DATABASE_URL","postgresql+psycopg://kats:secret@localhost/kats?sslmode=verify-full")
    monkeypatch.setenv("SECRET_KEY","production-app-secret-a"*3)
    monkeypatch.setenv("JWT_SECRET_KEY","production-jwt-secret-b"*3)
    monkeypatch.setenv("REDIS_URL","redis://localhost:6379/0")
    # The local test runner supplies memory:// and RATELIMIT_ENABLED=false.
    # A valid production baseline must explicitly override both values.
    monkeypatch.setenv("RATELIMIT_STORAGE_URI","redis://localhost:6379/0")
    monkeypatch.setenv("RATELIMIT_ENABLED","true")
    monkeypatch.setenv("COOKIE_SECURE","true")
    monkeypatch.setenv("CORS_ORIGINS","https://kats.example.test")
    monkeypatch.setenv("PUBLIC_REGISTRATION_ENABLED","false")

def test_production_cors_rejects_wildcards_mixed_origins_and_self_registration(monkeypatch):
    configure(monkeypatch)
    validate_production_config()
    for invalid in ("https://kats.example.test,http://evil.test",
                    "https://*","https://user:secret@kats.example.test",
                    "https://kats.example.test/fake-path"):
        monkeypatch.setenv("CORS_ORIGINS",invalid)
        with pytest.raises(RuntimeError):
            validate_production_config()
    monkeypatch.setenv("CORS_ORIGINS","https://kats.example.test")
    monkeypatch.setenv("PUBLIC_REGISTRATION_ENABLED","true")
    with pytest.raises(RuntimeError):
        validate_production_config()


def test_production_rejects_memory_rate_limiter_even_with_valid_redis(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "memory://")
    with pytest.raises(RuntimeError, match="requires Redis"):
        validate_production_config()


def test_production_rejects_disabled_rate_limiting(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("RATELIMIT_ENABLED", "false")
    with pytest.raises(RuntimeError, match="cannot disable API rate limiting"):
        validate_production_config()


def test_production_rejects_insecure_postgres_connection_and_secret_reuse(monkeypatch):
    configure(monkeypatch)
    for uri in (
        "postgresql+psycopg://kats:secret@localhost/kats",
        "postgresql+psycopg://kats:secret@localhost/kats?sslmode=require",
        "postgresql+psycopg://kats@localhost/kats?sslmode=verify-full",
    ):
        monkeypatch.setenv("DATABASE_URL", uri)
        with pytest.raises(RuntimeError, match="PostgreSQL"):
            validate_production_config()
    configure(monkeypatch)
    monkeypatch.setenv("JWT_SECRET_KEY", "production-app-secret-a" * 3)
    with pytest.raises(RuntimeError, match="independently"):
        validate_production_config()


def test_production_rejects_database_connection_overcommit(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("DB_POOL_SIZE", "30")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "15")
    monkeypatch.setenv("DB_CONNECTION_BUDGET", "80")
    with pytest.raises(RuntimeError, match="connection budget"):
        validate_production_config()
    monkeypatch.setenv("DB_POOL_SIZE", "5")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "2")
    validate_production_config()


def test_vercel_client_preview_origin_is_exact_not_wildcard(monkeypatch):
    from app.config import configured_origins, vercel_deployment_origin
    configure(monkeypatch)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("VERCEL_URL", "kats-client-3f2a-abc.vercel.app")
    assert vercel_deployment_origin() == "https://kats-client-3f2a-abc.vercel.app"
    assert configured_origins() == [
        "https://kats.example.test", "https://kats-client-3f2a-abc.vercel.app"
    ]
    validate_production_config()

    for bad in (
        "*.vercel.app", "evil.vercel.app.attacker.com",
        "https://example.vercel.app", "example.vercel.app/path",
        "example.vercel.app:443", "a..vercel.app",
        "-negative.vercel.app", "example.vercel.app.", "example.com", "",
    ):
        monkeypatch.setenv("VERCEL_URL", bad)
        with pytest.raises(RuntimeError, match="VERCEL_URL"):
            validate_production_config()
    monkeypatch.setenv("VERCEL_URL", "kats-client-3f2a-abc.vercel.app")
    monkeypatch.setenv("VERCEL_ENV", "development")
    with pytest.raises(RuntimeError, match="deployment environment"):
        validate_production_config()
    monkeypatch.delenv("VERCEL", raising=False)
    assert vercel_deployment_origin() is None
    assert configured_origins() == ["https://kats.example.test"]
    validate_production_config()


def test_explicit_vercel_origin_always_preserves_hostwares_allowlist(monkeypatch):
    from app.config import configured_origins
    configure(monkeypatch)
    monkeypatch.setenv("CORS_ORIGINS", "https://kats.example.test,https://client-preview.vercel.app")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("VERCEL_URL", "client-preview.vercel.app")
    assert configured_origins() == ["https://kats.example.test", "https://client-preview.vercel.app"]
    validate_production_config()
