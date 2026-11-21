"""Initialize an isolated SQLite schema for Docker-free local development.

This file creates tables only in the ignored preview database; it does not
run Alembic, touch PostgreSQL, or enable any live providers.
"""
from __future__ import annotations
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACK = ROOT / "backend"
if str(BACK) not in sys.path:
    sys.path.insert(0, str(BACK))


def main():
    if os.environ.get("APP_ENV") != "development" or os.environ.get("KATS_PREVIEW_MODE") != "1":
        raise SystemExit("Refusing preview DB initialization outside development preview.")
    from app import create_app
    from app.extensions import db
    app = create_app()
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    dbfile = (ROOT / ".local" / "kats-preview.sqlite3").resolve()
    if uri != "sqlite:///" + dbfile.as_posix():
        raise SystemExit("Refusing SQLite initialization outside the designated ignored preview DB.")
    dbfile.parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        db.create_all()
        # create_all leaves existing preview tables intact. Add the two nullable
        # or defaulted fields without replacing any fictional records.
        from sqlalchemy import inspect, text
        with db.engine.begin() as connection:
            inspector = inspect(connection)
            if "advance_id" not in {c["name"] for c in inspector.get_columns("payments")}:
                connection.execute(text("ALTER TABLE payments ADD COLUMN advance_id VARCHAR(36) REFERENCES rent_advances(id)"))
                connection.execute(text("CREATE INDEX ix_payments_advance_id ON payments(advance_id)"))
            if "book_code" not in {c["name"] for c in inspector.get_columns("bank_statements")}:
                connection.execute(text("ALTER TABLE bank_statements ADD COLUMN book_code VARCHAR(40) NOT NULL DEFAULT 'BANK'"))
    print("[PREVIEW] SQLite schema ready at .local/kats-preview.sqlite3", flush=True)


if __name__ == "__main__":
    main()
