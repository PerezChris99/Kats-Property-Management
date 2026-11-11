import os
from datetime import timedelta

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///local-dev.sqlite3")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    # Pool bounds are applied dynamically in create_app only for PostgreSQL.
    # Avoid adding pooling kwargs to SQLite in lightweight unit tests.
    JSON_MAX_BYTES = int(os.getenv("JSON_MAX_BYTES", "262144"))
    RATELIMIT_HEADERS_ENABLED = True
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-unsafe-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development-only-not-a-real-jwt-secret-use-env")
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_REFRESH_COOKIE_PATH = "/api/v1/auth"
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI") or os.getenv("REDIS_URL", "memory://")
    # Permit disabling limits for disposable, high-volume browser tests only.
    # validate_production_config() rejects this in any production process.
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() != "false"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    SQLALCHEMY_ECHO = False
    PROPAGATE_EXCEPTIONS = False

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
    from urllib.parse import urlparse, parse_qs
    parsed_db = urlparse(os.environ["DATABASE_URL"])
    mode = parse_qs(parsed_db.query).get("sslmode", [""])[0]
    if not parsed_db.hostname or not parsed_db.username or not parsed_db.password:
        raise RuntimeError("Production PostgreSQL URL requires a host, restricted user and password")
    if mode != "verify-full":
        raise RuntimeError("Production PostgreSQL requires sslmode=verify-full with verified certificates")
    if os.environ["SECRET_KEY"] == os.environ["JWT_SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY and JWT_SECRET_KEY must be independently generated")
    if os.getenv("COOKIE_SECURE") != "true":
        raise RuntimeError("Production requires COOKIE_SECURE=true")
    origins = [x.strip() for x in os.environ["CORS_ORIGINS"].split(",") if x.strip()]
    if not origins:
        raise RuntimeError("At least one HTTPS CORS origin is required")
    for origin in origins:
        p = urlparse(origin)
        if (p.scheme != "https" or not p.hostname or p.username or p.password or
                p.path not in ("", "/") or p.query or p.fragment or "*" in origin):
            raise RuntimeError("Production CORS origins must be explicit HTTPS hosts without paths or wildcards")
    if os.getenv("PUBLIC_REGISTRATION_ENABLED", "false").lower() == "true":
        raise RuntimeError("Public self-registration requires a verified-email workflow; use invitations")
    storage = os.getenv("RATELIMIT_STORAGE_URI") or os.getenv("REDIS_URL", "")
    if not storage.startswith(("redis://", "rediss://")):
        raise RuntimeError("Production rate limiting requires Redis; memory storage is not safe across workers")
    if os.getenv("RATELIMIT_ENABLED", "true").lower() == "false":
        raise RuntimeError("Production cannot disable API rate limiting")
    if os.getenv("S3_BUCKET") and (not os.getenv("CLAMAV_HOST") or not os.getenv("S3_ENDPOINT_URL")):
        raise RuntimeError("Production document storage requires a private ClamAV scanner and S3 endpoint")
    if os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true" and os.getenv("APP_BEHIND_TRUSTED_PROXY", "false").lower() != "true":
        raise RuntimeError("Only trust X-Forwarded headers behind a verified and sanitizing reverse proxy")
    try:
        pool = int(os.getenv("DB_POOL_SIZE", "5"))
        overflow = int(os.getenv("DB_MAX_OVERFLOW", "2"))
        timeout = int(os.getenv("DB_POOL_TIMEOUT", "10"))
        if not 1 <= pool <= 30 or not 0 <= overflow <= 15 or not 1 <= timeout <= 60:
            raise ValueError()
        workers = int(os.getenv("API_WORKERS", "2"))
        celery_workers = int(os.getenv("CELERY_WORKER_CONCURRENCY", "2"))
        budget = int(os.getenv("DB_CONNECTION_BUDGET", "80"))
        # API/worker pools are per-process. Reserve 10 slots for migrations,
        # administration, managed backup tools and incident recovery.
        if (not 1 <= workers <= 16 or not 1 <= celery_workers <= 16
                or not 20 <= budget <= 1000
                or (workers + celery_workers) * (pool + overflow) + 10 > budget):
            raise ValueError()
    except ValueError:
        raise RuntimeError("Database pool or connection budget exceeds configured safe capacity") from None

