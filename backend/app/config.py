import os
from datetime import timedelta

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///local-dev.sqlite3")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-unsafe-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development-only-not-a-real-jwt-secret-use-env")
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_REFRESH_COOKIE_PATH = "/api/v1/auth"
    RATELIMIT_STORAGE_URI = os.getenv("REDIS_URL", "memory://")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    SQLALCHEMY_ECHO = False

def validate_production_config():
    if os.getenv("APP_ENV", "development") != "production":
        return
    required = ("DATABASE_URL", "SECRET_KEY", "JWT_SECRET_KEY", "REDIS_URL", "CORS_ORIGINS")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("Missing production environment variables: " + ", ".join(missing))
    for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
        secret = os.environ[key]
        if len(secret) < 32 or secret.startswith("REPLACE") or secret.startswith("development"):
            raise RuntimeError(key + " must be an unpredictable secret")
    if not os.environ["DATABASE_URL"].startswith("postgresql"):
        raise RuntimeError("PostgreSQL is required for production")
    if os.getenv("COOKIE_SECURE") != "true":
        raise RuntimeError("Production requires COOKIE_SECURE=true")
    if not os.environ["CORS_ORIGINS"].startswith("https://"):
        raise RuntimeError("Production requires an HTTPS CORS origin")
