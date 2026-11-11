import logging
import os
import secrets
from urllib.parse import urlparse
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from sqlalchemy import text
from werkzeug.exceptions import HTTPException
from .config import Config, validate_production_config
from .extensions import db, migrate, jwt, limiter

def create_app(test_config=None):
    if test_config is None:
        validate_production_config()
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config is not None:
        app.config.update(test_config)
    if str(app.config.get("SQLALCHEMY_DATABASE_URI", "")).startswith("postgresql"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            **app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}),
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "2")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "10")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
            "pool_use_lifo": True,
            "connect_args": {"options": "-c statement_timeout=15000 -c idle_in_transaction_session_timeout=30000"}
        }
    if os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true":
        # Trust exactly one hop; the frontend proxy MUST overwrite, not append,
        # externally supplied X-Forwarded-For and X-Forwarded-Proto values.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0)
    if os.getenv("APP_ENV") == "production":
        trusted = os.getenv("TRUSTED_HOSTS")
        app.config["TRUSTED_HOSTS"] = [h.strip() for h in trusted.split(",") if h.strip()] if trusted else [
            urlparse(x.strip()).hostname for x in os.environ["CORS_ORIGINS"].split(",") if x.strip()
        ]
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
    CORS(app, origins=allowed_origins, supports_credentials=True, resources={r"/api/*": {"origins": allowed_origins}})

    @app.before_request
    def validate_request():
        if not request.path.startswith("/api/"):
            return None
        if request.content_length and request.content_length > app.config["MAX_CONTENT_LENGTH"]:
            abort(413)
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if request.is_json and request.content_length and request.content_length > app.config["JSON_MAX_BYTES"]:
                abort(413, description="JSON request exceeds configured limit")
            origin = request.headers.get("Origin")
            # Browser mutations with an Origin must originate from an explicitly
            # approved frontend, even when the endpoint itself is public.
            if origin and origin not in allowed_origins:
                abort(403, description="Origin not allowed")
            if request.content_length and request.content_length > 0 and not request.is_json:
                abort(415, description="Mutations require application/json")
        return None

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["X-Request-ID"] = secrets.token_hex(12)
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if request.is_secure and os.getenv("APP_ENV") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error={"code": error.name.upper().replace(" ", "_"), "message": error.description}), error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        # Production must not log request bodies, query strings, credentials,
        # exception messages or SQL bind values.
        if os.getenv("APP_ENV") == "production":
            app.logger.error("Internal error type=%s endpoint=%s", type(error).__name__, request.endpoint or "unknown")
        else:
            app.logger.exception("Unhandled exception")
        return jsonify(error={"code": "INTERNAL_ERROR", "message": "Unexpected server error"}), 500

    @app.get("/healthz")
    @limiter.exempt
    def health():
        return jsonify(status="ok")

    @app.get("/readyz")
    @limiter.exempt
    def ready():
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ready")

    from . import models  # noqa: F401
    from . import extra_models  # noqa: F401
    from . import utility_models  # noqa: F401
    from . import privacy_models  # noqa: F401
    from . import dispute_models  # noqa: F401
    from . import maintenance_plan_models  # noqa: F401
    from . import account_models  # noqa: F401
    from .api import api
    app.register_blueprint(api, url_prefix="/api/v1")
    from .mfa import mfa_api
    app.register_blueprint(mfa_api, url_prefix="/api/v1")
    from .extra_api import extra_api
    app.register_blueprint(extra_api, url_prefix="/api/v1")
    from .documents import documents_api
    app.register_blueprint(documents_api, url_prefix="/api/v1")
    from .mobile_payments import mobile_api
    app.register_blueprint(mobile_api, url_prefix="/api/v1")
    from .leases_deposits import lifecycle_api
    app.register_blueprint(lifecycle_api, url_prefix="/api/v1")
    from .property_hierarchy import hierarchy_api
    app.register_blueprint(hierarchy_api, url_prefix="/api/v1")
    from .account_recovery import recovery_api
    app.register_blueprint(recovery_api, url_prefix="/api/v1")
    from .proration import proration_api
    app.register_blueprint(proration_api, url_prefix="/api/v1")
    from .analytics import analytics_api
    app.register_blueprint(analytics_api, url_prefix="/api/v1")
    from .portfolio_edit import portfolio_api
    app.register_blueprint(portfolio_api, url_prefix="/api/v1")
    from .report_exports import report_api
    app.register_blueprint(report_api, url_prefix="/api/v1")
    from .utilities import utility_api
    app.register_blueprint(utility_api, url_prefix="/api/v1")
    from .privacy import privacy_api
    app.register_blueprint(privacy_api, url_prefix="/api/v1")
    from .disputes import dispute_api
    app.register_blueprint(dispute_api, url_prefix="/api/v1")
    from .maintenance_plans import maintenance_plan_api
    app.register_blueprint(maintenance_plan_api, url_prefix="/api/v1")
    from .document_rls import begin_document_scope, clear_document_scope

    @app.before_request
    def establish_database_actor_scope():
        # JWT claims are verified against server-side session_version, and
        # PostgreSQL SET LOCAL is transaction-bound. Public routes are excluded
        # so stale browser cookies never block a fresh sign-in.
        if not request.path.startswith("/api/"):
            return
        if request.path.startswith("/api/v1/public/") or request.path in (
            "/api/v1/auth/login", "/api/v1/auth/register",
            "/api/v1/auth/recover", "/api/v1/auth/complete-token",
            "/api/v1/auth/demo-accounts", "/api/v1/auth/demo-sign-in",
        ):
            return
        begin_document_scope()

    app.teardown_request(clear_document_scope)
    from .cli import register_commands
    register_commands(app)
    return app
