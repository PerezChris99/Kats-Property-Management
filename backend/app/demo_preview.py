"""Local preview demo access guard.

Demo accounts may be chosen without a password ONLY against the exact,
ignored SQLite preview database and from loopback. Production, tests,
PostgreSQL development and network clients are always denied.
"""
from __future__ import annotations

import os
from pathlib import Path
from flask import current_app, request

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = ROOT / ".local" / "kats-preview.sqlite3"


def preview_uri() -> str:
    return "sqlite:///" + EXPECTED.resolve().as_posix()


def demo_preview_enabled(app=None) -> bool:
    if os.getenv("APP_ENV") != "development":
        return False
    if os.getenv("KATS_PREVIEW_MODE") != "1":
        return False
    if os.getenv("DATABASE_URL") != preview_uri():
        return False
    if not EXPECTED.is_file():
        return False
    actual_app = app or current_app
    return actual_app.config.get("SQLALCHEMY_DATABASE_URI") == preview_uri() and not actual_app.config.get("TESTING", False)


def assert_preview_database(app=None) -> None:
    # Before app initialization, require all environment and path guards.
    if (os.getenv("APP_ENV") != "development"
        or os.getenv("KATS_PREVIEW_MODE") != "1"
        or os.getenv("DATABASE_URL") != preview_uri()
        or not EXPECTED.is_file()):
        raise RuntimeError("Demo seed is restricted to local .local/kats-preview.sqlite3 (APP_ENV=development, KATS_PREVIEW_MODE=1).")
    if app is not None and not demo_preview_enabled(app):
        raise RuntimeError("Demo seed is disabled for this application configuration.")


def demo_http_allowed() -> bool:
    # A local reverse proxy can make external traffic appear to originate from
    # loopback; require the public-facing HTTP Host to be loopback too.
    from urllib.parse import urlsplit
    hostname = urlsplit("//" + request.host).hostname
    if hostname not in ("127.0.0.1", "localhost", "::1"):
        return False
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return False
    return demo_preview_enabled()
