import logging
import os
from flask import Flask, jsonify, request
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
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
    CORS(app, origins=allowed_origins, supports_credentials=True, resources={r"/api/*": {"origins": allowed_origins}})

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error={"code": error.name.upper().replace(" ", "_"), "message": error.description}), error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Unhandled exception")
        return jsonify(error={"code": "INTERNAL_ERROR", "message": "Unexpected server error"}), 500

    @app.get("/healthz")
    def health():
        return jsonify(status="ok")

    @app.get("/readyz")
    def ready():
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ready")

    from . import models  # noqa: F401
    from . import extra_models  # noqa: F401
    from .api import api
    app.register_blueprint(api, url_prefix="/api/v1")
    from .extra_api import extra_api
    app.register_blueprint(extra_api, url_prefix="/api/v1")
    from .documents import documents_api
    app.register_blueprint(documents_api, url_prefix="/api/v1")
    from .mobile_payments import mobile_api
    app.register_blueprint(mobile_api, url_prefix="/api/v1")
    from .cli import register_commands
    register_commands(app)
    return app
