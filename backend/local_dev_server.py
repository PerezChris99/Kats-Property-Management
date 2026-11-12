"""Visible, guarded local PostgreSQL development Flask server.

Only for the dedicated localhost kats_demo runtime account. Never expose it
outside loopback, and never mutate schema or seed tenant records at startup.
"""
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    print("[boot] Checking isolated PostgreSQL demo environment...", flush=True)
    uri = os.environ.get("DATABASE_URL", "")
    try:
        parsed = urlsplit(uri.replace("postgresql+psycopg://", "postgresql://", 1))
        port = int(os.environ.get("KATS_LOCAL_PG_PORT", "0"))
        if (os.environ.get("APP_ENV") != "development"
                or os.environ.get("KATS_LOCAL_PG_DEMO") != "1"
                or os.environ.get("KATS_PREVIEW_MODE") == "1"
                or parsed.scheme != "postgresql"
                or parsed.hostname != "127.0.0.1"
                or parsed.username != "kats_demo_runtime"
                or parsed.path != "/kats_demo" or parsed.port != port
                or not parsed.password):
            raise RuntimeError("Flask can only start against the restricted localhost kats_demo runtime")
        print("[boot] Loading Flask application (this may be slower on cold Windows starts)...", flush=True)
        from app import create_app
        from app.extensions import db
        from sqlalchemy import text
        app = create_app()
        print("[boot] Checking PostgreSQL SELECT 1 with the runtime account...", flush=True)
        with app.app_context():
            db.session.execute(text("SELECT 1"))
            db.session.remove()
        print("[boot] Flask + PostgreSQL connected; binding 127.0.0.1...", flush=True)
        port_data = json.loads((ROOT / "ops" / "dev_ports.json").read_text(encoding="utf-8"))
        api_port = port_data["backend"]
        if type(api_port) is not int or not (1024 <= api_port <= 65535):
            raise RuntimeError("Invalid configured backend port")
        app.run(host="127.0.0.1", port=api_port, debug=False,
                use_reloader=False, threaded=True)
        return 0
    except (OSError, ValueError, RuntimeError, ImportError, Exception) as exc:
        # Local development only. Preserve a useful exception type without
        # echoing connection strings, credentials, or SQL statement parameters.
        print("[ERROR] Local Flask bootstrap " + type(exc).__name__ +
              ": " + str(exc).splitlines()[0][:320], file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
