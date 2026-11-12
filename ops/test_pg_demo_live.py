"""Real-process localhost PostgreSQL Flask readiness and demo-account test.

CI-only acceptance. Uses the marker-bound kats_demo_runtime user, starts an
independent Flask process, confirms real HTTP readiness and all 31 demo
accounts, then shuts down. Never connects to hosted/production databases.
"""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import local_postgres_demo as pg

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=4) as response:
        return response.status, json.load(response)


def run():
    values = pg.load()
    pg.marker(values, pg.RUNTIME)
    env = pg.environ(values, pg.RUNTIME)
    if env["DATABASE_URL"] != pg.uri(values, pg.RUNTIME):
        raise RuntimeError("Unexpected test database; refusing to start.")
    # Flask logs go to a bounded local spool so errors can be printed when
    # readiness fails, without blocking on an unread stdout pipe.
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as logs:
        proc = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "backend" / "local_dev_server.py")],
            cwd=ROOT / "backend", env=env,
            stdout=logs, stderr=subprocess.STDOUT
        )
        try:
            limit = time.monotonic() + 105
            last_error = "Flask did not bind"
            while time.monotonic() < limit:
                if proc.poll() is not None:
                    raise RuntimeError(f"Flask stopped early (exit {proc.returncode})")
                try:
                    status, data = get("/readyz")
                    if status == 200 and data.get("status") == "ready":
                        break
                    last_error = "Non-ready SQL readiness body"
                except (OSError, ValueError, KeyError) as exc:
                    last_error = type(exc).__name__
                time.sleep(0.7)
            else:
                raise RuntimeError("Flask SQL readiness timed out: " + last_error)
            status, payload = get("/api/v1/auth/demo-accounts")
            assert status == 200 and payload.get("enabled"), payload
            assert len(payload.get("accounts", [])) == 31, payload
            assert payload["accounts"][0]["key"] == "landlord"
            request = urllib.request.Request(
                BASE + "/api/v1/auth/demo-sign-in", method="POST",
                data=json.dumps({"account": "landlord"}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                signed = json.load(response)
                assert response.status == 200 and signed["user"]["role"] == "OWNER"
            print("[PASS] Real Flask child process on localhost PostgreSQL: "
                  "/readyz + 31 demo logins + owner cookie sign-in", flush=True)
        except Exception:
            logs.flush()
            logs.seek(0)
            tail = logs.read()[-8000:]
            print("[Flask captured startup output] \n" + tail, file=sys.stderr,
                  flush=True)
            raise
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)


if __name__ == "__main__":
    run()
