import pytest
from app.config import validate_production_config

def configure(monkeypatch):
    monkeypatch.setenv("APP_ENV","production")
    monkeypatch.setenv("DATABASE_URL","postgresql+psycopg://kats@localhost/kats")
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
