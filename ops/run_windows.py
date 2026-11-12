"""Native Windows development launcher invoked by root .bat scripts.

Starts React and Flask in separate Windows/VS Code terminal panes. Uses Docker-backed
PostgreSQL/Redis when available; if Docker is absent, safely falls back to
an isolated SQLite-only local preview with no Celery worker or Beat.
No operational .env or database is read or modified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import signal
import threading
import urllib.error
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
FRONT = ROOT / "frontend"
BACK = ROOT / "backend"
STATE = ROOT / ".local"
VENV = ROOT / ".venv"
CONFIG = ROOT / ".env.native"
COMPOSE = ROOT / "compose.native-deps.yml"
PROJECT = "kats-native"
PG_DEMO_CONFIG = ROOT / ".env.pg-demo"
DEV_MODE_FILE = STATE / "dev-mode.json"
class StartupError(RuntimeError):
    pass

# Single local-only port contract shared by launcher and Vite.
def load_service_ports():
    try:
        ports = json.loads((ROOT / "ops" / "dev_ports.json").read_text(encoding="utf-8"))
        frontend, backend = ports["frontend"], ports["backend"]
        if (type(frontend) is not int or type(backend) is not int
                or not (1024 <= frontend <= 65535)
                or not (1024 <= backend <= 65535)
                or frontend == backend):
            raise ValueError("ports must be distinct")
        return frontend, backend
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise StartupError("Invalid ops/dev_ports.json: two distinct ports (1024–65535) required") from exc

FRONTEND_PORT, BACKEND_PORT = load_service_ports()
FRONTEND_ORIGIN = f"http://127.0.0.1:{FRONTEND_PORT}"
BACKEND_ORIGIN = f"http://127.0.0.1:{BACKEND_PORT}"


def invoke(argv, cwd=ROOT, env=None):
    result = subprocess.run(argv, cwd=str(cwd), env=env, check=False)
    if result.returncode:
        raise StartupError(f"{argv[0]} failed with exit code {result.returncode}; see output above.")

def require(executable):
    result = shutil.which(executable)
    if not result:
        raise StartupError(f"Missing {executable}; install it, then reopen VS Code.")
    return result

def config():
    if not CONFIG.exists():
        new = {
            "KATS_LOCAL_ONLY": "1",
            "POSTGRES_DB": "kats_native",
            "POSTGRES_USER": "kats_native",
            "POSTGRES_PASSWORD": secrets.token_hex(24),
            "SECRET_KEY": secrets.token_hex(32),
            "JWT_SECRET_KEY": secrets.token_hex(32),
        }
        # Frontend/backend start concurrently in split terminal panes.
        # Write a complete temp file and atomically create the final path with
        # os.link; the losing process reads the winner's FULL config. Never
        # overwrite an existing file (including an edited local config).
        temp = CONFIG.with_name(CONFIG.name + "." + secrets.token_hex(8) + ".tmp")
        try:
            with temp.open("x", encoding="utf-8") as target:
                target.writelines(f"{key}={value}\n" for key, value in new.items())
            try:
                os.link(temp, CONFIG)
                print("[setup] Generated ignored .env.native with isolated local secrets.", flush=True)
            except FileExistsError:
                pass
        finally:
            temp.unlink(missing_ok=True)
    result = {}
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            raise StartupError("Invalid .env.native entry.")
        result[key.strip()] = value.strip()
    if (result.get("KATS_LOCAL_ONLY") != "1"
        or result.get("POSTGRES_DB") != "kats_native"
        or result.get("POSTGRES_USER") != "kats_native"
        or len(result.get("POSTGRES_PASSWORD", "")) != 48
        or any(char not in "0123456789abcdef" for char in result["POSTGRES_PASSWORD"])
        or len(result.get("SECRET_KEY", "")) < 32
        or len(result.get("JWT_SECRET_KEY", "")) < 32):
        raise StartupError("Unsafe .env.native; expected local-only generated credentials.")
    return result

def environment(settings, preview=False):
    values = os.environ.copy()
    values.update({
        "APP_ENV": "development",
        "DATABASE_URL": "postgresql+psycopg://kats_native:" + settings["POSTGRES_PASSWORD"]
                        + "@127.0.0.1:55432/kats_native",
        "POSTGRES_PASSWORD": settings["POSTGRES_PASSWORD"],
        "SECRET_KEY": settings["SECRET_KEY"],
        "JWT_SECRET_KEY": settings["JWT_SECRET_KEY"],
        "REDIS_URL": "redis://127.0.0.1:56379/0",
        "RATELIMIT_STORAGE_URI": "redis://127.0.0.1:56379/0",
        "CELERY_BROKER_URL": "redis://127.0.0.1:56379/1",
        "CELERY_RESULT_BACKEND": "redis://127.0.0.1:56379/2",
        "CORS_ORIGINS": f"http://localhost:{FRONTEND_PORT},http://127.0.0.1:{FRONTEND_PORT}",
        "PUBLIC_APP_URL": f"http://localhost:{FRONTEND_PORT}",
        "PUBLIC_REGISTRATION_ENABLED": "false",
        "COOKIE_SECURE": "false",
        "MTN_MOMO_ENABLED": "false",
        "AIRTEL_MONEY_ENABLED": "false",
        "EFRIS_ENABLED": "false",
        "EMAIL_PROVIDER_ENABLED": "false",
        "SMS_PROVIDER_ENABLED": "false",
        "TRUST_PROXY_HEADERS": "false",
    })
    for key in ("S3_BUCKET", "S3_ENDPOINT_URL", "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY", "SMTP_HOST", "SMTP_PASSWORD",
                "AIRTEL_MONEY_CLIENT_SECRET", "MTN_MOMO_API_KEY"):
        values.pop(key, None)
    # Do not inherit a preview task mode into Docker-backed execution.
    values.pop("KATS_PREVIEW_MODE", None)
    values.pop("CELERY_TASK_ALWAYS_EAGER", None)
    if preview:
        # SQLite is only for local UI/API previews; never production/integration.
        # Database file stays inside ignored .local, separate from operational data.
        values.update({
            "DATABASE_URL": "sqlite:///" + (STATE / "kats-preview.sqlite3").as_posix(),
            "REDIS_URL": "memory://",
            "RATELIMIT_STORAGE_URI": "memory://",
            "CELERY_BROKER_URL": "memory://",
            "CELERY_RESULT_BACKEND": "cache+memory://",
            "CELERY_TASK_ALWAYS_EAGER": "true",
            "KATS_PREVIEW_MODE": "1",
        })
    return values

def read_pg_demo_config():
    """Read only the ignored, dedicated localhost demo credentials."""
    if not PG_DEMO_CONFIG.is_file():
        raise StartupError("No .env.pg-demo. Run unified Dev prepare first.")
    values = {}
    for line in PG_DEMO_CONFIG.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not key.strip() or not value:
            raise StartupError("Malformed dedicated PostgreSQL demo configuration.")
        values[key.strip()] = value.strip()
    if (not values.get("KATS_DEMO_INSTANCE")
            or len(values["KATS_DEMO_INSTANCE"]) != 32
            or not values.get("RUNTIME_PASSWORD")
            or len(values["RUNTIME_PASSWORD"]) < 32
            or not values.get("KATS_PG_DEMO_PORT","").isdigit()
            or not 1024 <= int(values["KATS_PG_DEMO_PORT"]) <= 65535
            or not values.get("SECRET_KEY") or not values.get("JWT_SECRET_KEY")):
        raise StartupError("Unsafe PostgreSQL demo config; run the dedicated demo setup.")
    return values


def dev_mode():
    """A successful preparation selects ONE database for BOTH service tasks."""
    try:
        selected = json.loads(DEV_MODE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StartupError(
            "Unified development database has not been prepared. Run "
            "'KATS: Start Dev (Frontend + Backend)' (not the backend pane alone)."
        ) from exc
    if (selected.get("root") != str(ROOT.resolve())
            or selected.get("mode") not in ("pgdemo", "preview")
            or not isinstance(selected.get("prepared_at"), int)
            or time.time() - selected["prepared_at"] > 4 * 60 * 60
            or selected["prepared_at"] > time.time() + 60):
        raise StartupError("Stale or invalid unified development session; run the combined start task.")
    return selected["mode"]


def pg_demo_environment(settings):
    """Execute ONLY as the isolated non-superuser PostgreSQL demo runtime role."""
    values = read_pg_demo_config()
    out = environment(settings, preview=True)  # memory-only workers, no provider keys
    out.pop("KATS_PG_ADMIN_PASSWORD", None)
    out.update({
        "APP_ENV": "development",
        "KATS_PREVIEW_MODE": "0",
        "KATS_SEED_DEMO": "1",
        "KATS_LOCAL_PG_DEMO": "1",
        "KATS_LOCAL_PG_INSTANCE": values["KATS_DEMO_INSTANCE"],
        "KATS_LOCAL_PG_PORT": values["KATS_PG_DEMO_PORT"],
        "DATABASE_URL": (
            "postgresql+psycopg://kats_demo_runtime:"
            + quote(values["RUNTIME_PASSWORD"], safe="")
            + "@127.0.0.1:" + values["KATS_PG_DEMO_PORT"] + "/kats_demo"
        ),
        "SECRET_KEY": values["SECRET_KEY"],
        "JWT_SECRET_KEY": values["JWT_SECRET_KEY"],
    })
    return out


def dev_prepare():
    """One VS Code command: install/build, seed isolated local PG, else preview.

    Never seed on ambiguous PG credentials, marker mismatches or occupied app
    ports; these are failures rather than reasons to silently use SQLite.
    """
    started_at = time.time()
    if port_open(BACKEND_PORT):
        raise StartupError(
            "KATS backend already occupies the API port. Use the Stop task "
            "before switching demo databases; existing records are untouched."
        )
    # A failed preparation must not leave an older database choice usable.
    DEV_MODE_FILE.unlink(missing_ok=True)
    config()  # independent local-only config; never read operational .env
    frontend(build=True)
    python = backend()
    requested = os.getenv("KATS_DEMO_DB", "auto").lower().strip()
    if requested not in ("auto", "postgres", "sqlite"):
        raise StartupError("KATS_DEMO_DB must be auto, postgres, or sqlite.")
    if requested == "sqlite":
        choice = "preview"
    else:
        if PG_DEMO_CONFIG.exists():
            port = int(read_pg_demo_config()["KATS_PG_DEMO_PORT"])
        else:
            port_value = os.getenv("KATS_PG_DEMO_PORT", "5432")
            if not port_value.isdigit() or not 1024 <= int(port_value) <= 65535:
                raise StartupError("KATS_PG_DEMO_PORT must be a localhost TCP port.")
            port = int(port_value)
        choice = "pgdemo" if port_open(port) else "preview"
        if choice == "preview" and requested == "postgres":
            raise StartupError(
                f"Local PostgreSQL is not listening on 127.0.0.1:{port}. "
                "Start the PostgreSQL service; no SQLite fallback was authorized."
            )
    if choice == "pgdemo":
        print("[DEV] Local PostgreSQL detected: preparing kats_demo and 31 accounts...", flush=True)
        invoke([str(python), str(ROOT / "ops" / "local_postgres_demo.py"), "prepare"],
               cwd=ROOT, env=venv_environment(os.environ))
        invoke([str(python), str(ROOT / "ops" / "local_postgres_demo.py"), "check"],
               cwd=ROOT, env=venv_environment(os.environ))
    else:
        print("[FALLBACK] Local PostgreSQL unavailable or SQLite explicitly selected.", flush=True)
        print("[FALLBACK] Synthetic SQLite preview ONLY: no PostgreSQL RLS or Celery.", flush=True)
        settings = config()
        runtime = venv_environment(environment(settings, preview=True))
        invoke([str(python), str(ROOT / "ops" / "init_preview.py")],
               cwd=BACK, env=runtime)
        invoke([str(python), "-m", "flask", "--app", "wsgi", "seed-permissions"],
               cwd=BACK, env=runtime)
        invoke([str(python), str(ROOT / "ops" / "seed_demo_preview.py")],
               cwd=BACK, env=runtime)
    if stop_requested(started_at):
        raise StartupError("Stop was requested during demo preparation.")
    STATE.mkdir(exist_ok=True)
    temp = DEV_MODE_FILE.with_name(DEV_MODE_FILE.name + "." + secrets.token_hex(8) + ".tmp")
    try:
        temp.write_text(json.dumps({
            "mode": choice, "root": str(ROOT.resolve()),
            "accounts": 31, "prepared_at": int(time.time()),
        }), encoding="utf-8")
        os.replace(temp, DEV_MODE_FILE)
    finally:
        temp.unlink(missing_ok=True)
    print("[READY] Unified dev: " + ("local PostgreSQL kats_demo" if choice == "pgdemo"
          else "SQLite demo fallback") + ", 1 OWNER and 30 TENANT profiles.", flush=True)
    print("[NEXT] VS Code launches Flask and React in split integrated terminals.", flush=True)


def dev_doctor():
    verify_http_bridge()
    try:
        with urllib.request.urlopen(
            f"{FRONTEND_ORIGIN}/api/v1/auth/demo-accounts", timeout=6
        ) as response:
            payload = json.load(response)
    except (OSError, ValueError) as exc:
        raise StartupError("Demo account API is not available from the React origin.") from exc
    if (not payload.get("enabled") or
            len(payload.get("accounts", [])) != 31):
        raise StartupError("Expected one demo owner and 30 tenants, but demo accounts are missing.")
    print("[PASS] Combined Flask/React/SQL backend and all 31 demo logins visible.", flush=True)


def select_backend_mode():
    """Select isolated local development dependencies without touching prod."""
    requested = os.getenv("KATS_DEV_BACKEND", "auto").strip().lower()
    if requested not in ("auto", "docker", "preview", "unified"):
        raise StartupError("KATS_DEV_BACKEND must be auto, docker, preview, or unified.")
    if requested == "unified":
        return dev_mode()
    if requested == "preview":
        return "preview"
    docker = shutil.which("docker")
    if docker:
        try:
            # CLI presence alone does not mean the Desktop engine is running.
            ready = subprocess.run([docker, "info", "--format", "{{.ServerVersion}}"],
                                   capture_output=True, check=False, timeout=5)
            if ready.returncode == 0:
                return "docker"
        except (OSError, subprocess.TimeoutExpired):
            pass
    if requested == "docker":
        raise StartupError("Docker is required by KATS_DEV_BACKEND=docker. "
                           "Install Docker Desktop, or set KATS_DEV_BACKEND=preview "
                           "for a reduced SQLite-only development mode.")
    return "preview"

def prepare_backend(settings, python, mode):
    """Initialize either full Postgres or explicitly isolated SQLite preview."""
    preview = mode == "preview"
    STATE.mkdir(parents=True, exist_ok=True)
    runtime = venv_environment(environment(settings, preview=preview))
    if preview:
        print("[PREVIEW] Docker is unavailable or preview was selected.", flush=True)
        print("[PREVIEW] Using isolated .local/kats-preview.sqlite3 (SQLite); "
              "NO PostgreSQL RLS, Redis, Celery worker/Beat or scheduled tasks.", flush=True)
        print("[PREVIEW] Use Docker-backed mode for payments, concurrency, "
              "security integration and release acceptance.", flush=True)
        invoke([str(python), str(ROOT / "ops" / "init_preview.py")], cwd=BACK, env=runtime)
    else:
        print("[dependencies] Starting dedicated PostgreSQL + Redis in Docker...", flush=True)
        dependencies(["up", "-d", "--wait"], settings)
        invoke([str(python), "-m", "flask", "--app", "wsgi", "db", "upgrade"],
               cwd=BACK, env=runtime)
    print("[backend] Seeding new route permissions...", flush=True)
    invoke([str(python), "-m", "flask", "--app", "wsgi", "seed-permissions"],
           cwd=BACK, env=runtime)
    if preview and os.getenv("KATS_SEED_DEMO") == "1":
        print("[DEMO] Checking local landlord and tenant sample data...", flush=True)
        invoke([str(python), str(ROOT / "ops" / "seed_demo_preview.py")], cwd=BACK, env=runtime)
    return runtime

def frontend(*, build=False):
    """Install Node dependencies only if needed. Vite does not need a build."""
    node, npm = require("node"), require("npm.cmd")
    major = subprocess.run([node, "-p", "process.versions.node.split('.')[0]"],
                           capture_output=True, text=True, check=False)
    if major.returncode or not major.stdout.strip().isdigit() or int(major.stdout.strip()) < 20:
        raise StartupError("Node.js 20 or newer is required. Run setup after updating Node.")
    STATE.mkdir(exist_ok=True)
    lock = FRONT / "package-lock.json"
    stamp = STATE / "npm-lock.sha256"
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    vite = FRONT / "node_modules" / "vite" / "bin" / "vite.js"
    if (not vite.is_file() or not stamp.exists()
        or stamp.read_text(encoding="utf-8") != digest):
        print("[frontend] Installing changed or missing Node packages (first setup only)...", flush=True)
        invoke([npm, "ci", "--no-audit", "--no-fund"], cwd=FRONT)
        stamp.write_text(digest, encoding="utf-8")
    else:
        print("[frontend] Dependencies already installed; skipping npm ci.", flush=True)
    if build:
        print("[frontend] Running full JSX, lint, unit tests and release build...", flush=True)
        invoke([npm, "run", "build"], cwd=FRONT)
    else:
        print("[frontend] Starting Vite directly, without a full rebuild.", flush=True)
    return npm


def backend():
    """Prepare Python once; never run pip install repeatedly on every launch."""
    if sys.version_info < (3, 12):
        raise StartupError("Python 3.12+ is required.")
    python = VENV / "Scripts" / "python.exe"
    active = bool(os.environ.get("VIRTUAL_ENV") and
                  os.path.normcase(os.path.abspath(os.environ["VIRTUAL_ENV"]))
                  == os.path.normcase(str(VENV.resolve())))
    created = not python.is_file()
    if created:
        print("[backend] Creating isolated project .venv...", flush=True)
        invoke([sys.executable, "-m", "venv", str(VENV)])
    probe = subprocess.run([str(python), "-c",
                            "import sys; assert sys.version_info >= (3,12)"],
                           capture_output=True, check=False)
    if probe.returncode:
        raise StartupError("Existing .venv uses unsupported Python; recreate it after backing up any local settings.")
    print("[backend] " + ("Project .venv active." if active
                          else "Using isolated project .venv."), flush=True)
    STATE.mkdir(parents=True, exist_ok=True)
    requirements = BACK / "requirements.txt"
    stamp = STATE / "pip-requirements.sha256"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    needs_install = (created or (stamp.exists()
                     and stamp.read_text(encoding="utf-8") != digest))
    if not needs_install and not stamp.exists():
        # Backward compatibility for existing environments installed by the
        # old launcher. Never silently trust an empty/corrupted venv.
        modules = ("flask", "flask_sqlalchemy", "flask_migrate",
                   "flask_jwt_extended", "flask_cors", "flask_limiter",
                   "argon2", "psycopg", "redis", "celery", "boto3", "httpx",
                   "reportlab", "xlsxwriter", "cryptography")
        check = subprocess.run(
            [str(python), "-c",
             "import importlib.util,sys; sys.exit(not all("
             "importlib.util.find_spec(m) for m in " + repr(modules) + "))"],
            capture_output=True, check=False)
        deps = subprocess.run([str(python), "-m", "pip", "check"],
                              capture_output=True, check=False)
        needs_install = check.returncode != 0 or deps.returncode != 0
    if needs_install:
        print("[backend] Installing changed or missing Python dependencies...", flush=True)
        invoke([str(python), "-m", "pip", "install", "-r", str(requirements)])
    else:
        print("[backend] Dependencies already installed; skipping pip install.", flush=True)
    if needs_install or not stamp.exists():
        stamp.write_text(digest, encoding="utf-8")
    return python



def ready_frontend():
    """Fast-start Vite; setup/install belongs to the explicit setup task."""
    node = require("node")
    probe = subprocess.run(
        [node, "-p", "process.versions.node.split('.')[0]"],
        capture_output=True, text=True, check=False, timeout=4
    )
    if (probe.returncode or not probe.stdout.strip().isdigit()
            or int(probe.stdout.strip()) < 20):
        raise StartupError(
            "Frontend needs Node.js 20+ on PATH. Install/activate Node then reload VS Code."
        )
    vite = FRONT / "node_modules" / "vite" / "bin" / "vite.js"
    if not vite.is_file():
        raise StartupError(
            "Vite is not installed. Run 'KATS: Native setup (database + build)' "
            "once, or 'npm ci' in the frontend directory."
        )
    print("[React] Vite dependencies found; launching without npm install or build.",
          flush=True)
    return node


def ready_backend(mode):
    """Fast-start Flask against an already-initialized isolated local DB."""
    python = VENV / "Scripts" / "python.exe"
    if not python.is_file():
        raise StartupError(
            "Project Python .venv missing. Run 'KATS: Native setup (database + build)' "
            "once before starting."
        )
    # A cold Windows/Python startup can take longer than eight seconds.
    # Fast-start only needs to verify package presence; importing Flask and
    # extensions here needlessly repeats heavyweight imports before Flask boots.
    modules = ("flask", "flask_sqlalchemy", "flask_jwt_extended")
    check = (
        "import importlib.util,sys; "
        "sys.exit(0 if all(importlib.util.find_spec(m) is not None "
        "for m in " + repr(modules) + ") else 1)"
    )
    try:
        probe = subprocess.run(
            [str(python), "-c", check],
            capture_output=True, text=True, check=False, timeout=30,
            env=venv_environment(os.environ)
        )
    except subprocess.TimeoutExpired as exc:
        raise StartupError(
            "Python .venv dependency check exceeded 30 seconds. "
            "Check antivirus scanning, Python startup hooks and the .venv; "
            "then rerun the Native setup task if necessary."
        ) from exc
    except OSError as exc:
        raise StartupError(
            "Cannot start Python from the project .venv. "
            "Repair the virtual environment using the Native setup task."
        ) from exc
    if probe.returncode:
        raise StartupError(
            "Flask dependencies are missing or Python cannot inspect the .venv "
            "packages. Run the Native setup task once."
        )
    if mode == "preview" and not (STATE / "kats-preview.sqlite3").is_file():
        raise StartupError(
            "Local SQLite database not initialized. Run 'KATS: Native setup "
            "(database + build)' once; regular Start Dev never migrates databases."
        )
    print(f"[Flask] Existing {mode} environment found; starting without "
          "pip install, migrations or permission seeding.", flush=True)
    return python

def venv_environment(base):
    result = base.copy()
    result["VIRTUAL_ENV"] = str(VENV)
    result["PATH"] = str(VENV / "Scripts") + os.pathsep + result.get("PATH", "")
    result.pop("PYTHONHOME", None)
    return result

def dependencies(args, settings):
    invoke([require("docker"), "compose", "-p", PROJECT,
            "--env-file", str(CONFIG), "-f", str(COMPOSE), *args],
           env=environment(settings))

def port_open(port):
    """Inspect loopback only; never take over an unknown listener."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.75):
            return True
    except OSError:
        return False


def existing_kats_service(kind):
    """Recognize healthy KATS frontend/backend before spawning a duplicate."""
    port = FRONTEND_PORT if kind == "frontend" else BACKEND_PORT
    if not port_open(port):
        return False
    try:
        if kind == "frontend":
            with urllib.request.urlopen(f"{FRONTEND_ORIGIN}/", timeout=3) as result:
                html = result.read(16384).decode("utf-8", errors="replace")
                genuine = result.status == 200 and "<title>KATS" in html and "/src/main.jsx" in html
        else:
            with urllib.request.urlopen(f"{BACKEND_ORIGIN}/readyz", timeout=3) as result:
                info = json.load(result)
                genuine = (result.status == 200 and info.get("status") == "ready"
                           and bool(result.headers.get("X-Request-ID")))
            if genuine:
                try:
                    urllib.request.urlopen(f"{BACKEND_ORIGIN}/api/v1/auth/me", timeout=3)
                    genuine = False
                except urllib.error.HTTPError as exc:
                    genuine = (exc.code in (401, 422) and
                               bool(exc.headers.get("X-Request-ID")))
        if genuine:
            print(f"[reuse] Existing KATS {kind} is healthy at 127.0.0.1:{port}. "
                  "Leaving its terminal and process running.", flush=True)
            return True
    except (OSError, ValueError, KeyError, TypeError):
        pass
    raise StartupError(
        f"Port {port} is occupied by another or unhealthy application. "
        "Stop that process or use the native KATS Stop task; "
        "no unrelated service was terminated."
    )


def check_port(port):
    if port_open(port):
        raise StartupError(f"Port {port} is already occupied; avoid duplicate servers.")


def reachable(url):
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            return response.status == 200
    except OSError:
        return False

def stream_logs(name, process):
    """Mirror every live child stdout/stderr line into the running VS Code pane."""
    try:
        for line in process.stdout:
            print(f"[{name}] {line.rstrip()}", flush=True)
    except (OSError, ValueError):
        pass


def start_service(name, command, *, cwd, env, flags):
    # Avoid cmd.exe wrappers so Node/Python can receive process-group signals.
    proc = subprocess.Popen(
        command, cwd=str(cwd), env=env, creationflags=flags,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", bufsize=1
    )
    threading.Thread(target=stream_logs, args=(name, proc), daemon=True).start()
    print(f"[launch] {name} started (pid {proc.pid}); live logs follow.", flush=True)
    return name, proc


def kill_tree(process, timeout=8):
    """Ask a whole Windows process group to exit; force only after timeout."""
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.terminate()
        process.wait(timeout=timeout)
        return
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print(f"[stop] PID {process.pid} did not exit cleanly; forcing stop.", flush=True)
    if process.poll() is None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            process.kill()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass


STOP_FILE = STATE / "stop-request"


def stop_requested(started_at):
    try:
        return STOP_FILE.stat().st_mtime >= started_at
    except FileNotFoundError:
        return False


def verify_http_bridge():
    """Prove browser -> Vite -> Flask -> SQL, not a Vite index.html fallback."""
    try:
        with urllib.request.urlopen(f"{FRONTEND_ORIGIN}/readyz", timeout=5) as response:
            payload = json.load(response)
            if (response.status != 200 or payload.get("status") != "ready"
                    or not response.headers.get("X-Request-ID")):
                raise StartupError("Frontend /readyz is not Flask + database JSON.")
        with urllib.request.urlopen(f"{BACKEND_ORIGIN}/readyz", timeout=5) as response:
            payload = json.load(response)
            if response.status != 200 or payload.get("status") != "ready":
                raise StartupError("Flask database readiness check failed.")
        try:
            urllib.request.urlopen(f"{FRONTEND_ORIGIN}/api/v1/auth/me", timeout=5)
        except urllib.error.HTTPError as exc:
            if exc.code not in (401, 422) or not exc.headers.get("X-Request-ID"):
                raise StartupError("Proxied auth endpoint is not Flask-protected.") from exc
        else:
            raise StartupError("Unauthenticated auth/me unexpectedly allowed access.")
    except (OSError, ValueError, KeyError) as exc:
        raise StartupError("Frontend / API / database connection check failed. "
                           "Start both services and inspect the Flask log.") from exc
    print(f"[CONNECTED] React :{FRONTEND_PORT} -> Flask :{BACKEND_PORT} -> SQL readiness, auth 401: PASS", flush=True)

def launch(mode):
    started_at = time.time()
    settings = config()
    base = environment(settings)
    run_front = mode in ("start", "frontend")
    run_back = mode in ("start", "backend", "backend-stack")
    backend_mode = select_backend_mode() if run_back else None
    preview = backend_mode == "preview"
    # If the backend already runs, start only the missing frontend; likewise
    # preserve an existing KATS Vite server when starting the backend.
    reuse_front = existing_kats_service("frontend") if run_front else False
    reuse_back = existing_kats_service("backend") if run_back else False
    if preview and reuse_back and os.getenv("KATS_DEMO_STRICT") == "1":
        # Never silently reuse a PostgreSQL/ordinary backend for the demo task.
        try:
            with urllib.request.urlopen(
                f"{BACKEND_ORIGIN}/api/v1/auth/demo-accounts", timeout=3
            ) as response:
                existing_demo = json.load(response)
                usable = response.status == 200 and existing_demo.get("enabled") is True
        except (OSError, ValueError):
            usable = False
        if not usable:
            raise StartupError(
                "Another backend is already running on the KATS port, but it is "
                "not a ready local demo preview. Stop it using 'KATS: Stop "
                "(preserve database)', then run 'KATS: Demo start (landlord + "
                "30 tenants)'. Production/PostgreSQL data will not be reused."
            )
    quick = os.getenv("KATS_FAST_START") == "1"
    if run_front and not reuse_front:
        if quick:
            ready_frontend()
        else:
            frontend(build=False)
    python = (ready_backend(backend_mode) if quick else backend()) if (run_back and not reuse_back) else None
    if run_back and not reuse_back and backend_mode == "pgdemo":
        # The prepared mode is pinned; never silently attach to an ordinary
        # PostgreSQL instance or switch to SQLite if localhost PG disappears.
        invoke([str(python), str(ROOT / "ops" / "local_postgres_demo.py"), "check"],
               env=venv_environment(os.environ))
    runtime = ((venv_environment(pg_demo_environment(settings))
                if backend_mode == "pgdemo" else
                venv_environment(environment(settings, preview=preview))
                if quick else prepare_backend(settings, python, backend_mode))
               if run_back and not reuse_back else base)
    if run_back and not reuse_back and quick and preview and os.getenv("KATS_SEED_DEMO") == "1":
        # Fast-start still guarantees demo accounts on the isolated preview DB.
        invoke([str(python), str(ROOT / "ops" / "seed_demo_preview.py")],
               cwd=BACK, env=runtime)
    if stop_requested(started_at):
        print('[stop] Startup cancelled by stop request.', flush=True)
        return
    processes = []
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        if run_front and not reuse_front:
            node = require("node")
            # Spawn Node directly instead of npm.cmd so Ctrl+Break is deliverable.
            vite = FRONT / "node_modules" / "vite" / "bin" / "vite.js"
            processes.append(start_service("React", [node, str(vite),
                "--host", "127.0.0.1", "--port", str(FRONTEND_PORT), "--strictPort"],
                cwd=FRONT, env=base, flags=flags))
        if run_back and not reuse_back:
            runtime["PYTHONUNBUFFERED"] = "1"
            processes.append(start_service("Flask", [str(python), "-m", "flask",
                "--app", "wsgi", "run", "--host", "127.0.0.1", "--port", str(BACKEND_PORT),
                "--no-reload"], cwd=BACK, env=runtime, flags=flags))
            if mode in ("start", "backend-stack") and not preview and backend_mode != "pgdemo":
                STATE.mkdir(parents=True, exist_ok=True)
                processes.append(start_service("Celery worker", [str(python), "-m", "celery",
                    "-A", "app.tasks.celery_app", "worker", "--pool=solo",
                    "--loglevel=info"], cwd=BACK, env=runtime, flags=flags))
                processes.append(start_service("Celery beat", [str(python), "-m", "celery",
                    "-A", "app.tasks.celery_app", "beat", "--loglevel=info",
                    "--schedule", str(STATE / "celerybeat-schedule")],
                    cwd=BACK, env=runtime, flags=flags))
        until = time.monotonic() + 45
        while time.monotonic() < until:
            for name, proc in processes:
                if proc.poll() is not None:
                    raise StartupError(f"{name} exited early (exit {proc.returncode}).")
            if ((not run_front or reachable(f"{FRONTEND_ORIGIN}/"))
                and (not run_back or reachable(f"{BACKEND_ORIGIN}/readyz"))):
                break
            time.sleep(.5)
        else:
            raise StartupError("Service readiness timed out; inspect startup errors above.")
        ready = []
        if run_front:
            ready.append(f"React {FRONTEND_ORIGIN}" + (" (existing)" if reuse_front else " (started)"))
        if run_back:
            ready.append(f"Flask {BACKEND_ORIGIN}" + (" (existing)" if reuse_back else (" (SQLite PREVIEW)" if preview else " (started)")))
        print("\n[READY] " + " | ".join(ready), flush=True)
        print("[READY] Ctrl+C or stop.bat requests graceful shutdown.", flush=True)
        if reuse_front or reuse_back:
            print("[reuse] Only the newly started services are owned by this terminal. "
                  "Existing service logs remain in their original terminal.", flush=True)
        connected = False
        while True:
            if stop_requested(started_at):
                print("[stop] Stop requested from another terminal.", flush=True)
                break
            for name, proc in processes:
                if proc.poll() is not None:
                    raise StartupError(f"{name} exited (code {proc.returncode}).")
            # Both VS Code tasks start in parallel. Whichever becomes ready
            # last still triggers the same-origin API/SQL handshake, exactly
            # once per launcher and only after both endpoints answer.
            if (not connected
                    and reachable(f"{FRONTEND_ORIGIN}/")
                    and reachable(f"{BACKEND_ORIGIN}/readyz")):
                verify_http_bridge()
                connected = True
            time.sleep(.5)
    except KeyboardInterrupt:
        print("\n[stop] Stopping all launched services...", flush=True)
    finally:
        for name, proc in reversed(processes):
            print(f"[stop] Asking {name} to exit...", flush=True)
            kill_tree(proc)
        # Database files and PostgreSQL volumes survive application shutdown.

def windows_terminal_command(executable, root=ROOT):
    """Build two side-by-side panes in ONE Windows Terminal window.

    Backend is first/left; frontend is split to its right. Both are independent.
    -V creates a vertical divider (left/right), not an upper/lower split.
    """
    root = Path(root)
    frontend_batch = root / "start-frontend.bat"
    backend_batch = root / "ops" / "launch.bat"
    return [
        str(executable), "-w", "new",
        "new-tab", "--startingDirectory", str(root),
        "--title", "KATS Backend",
        "cmd.exe", "/k", f'call "{backend_batch}" backend-stack',
        ";",
        "split-pane", "-V", "--startingDirectory", str(root),
        "--title", "KATS Frontend",
        "cmd.exe", "/k", f'call "{frontend_batch}"',
    ]


def start_split():
    """Entry for start.bat: spawn two live Windows Terminal panes.

    The VS Code task uses the frontend/backend-stack modes instead; VS Code
    integrated terminal panes cannot be created from an arbitrary .bat file.
    """
    # Prepare before spawning panes so both use the same local credentials.
    config()
    terminal = shutil.which("wt.exe") or shutil.which("wt")
    if not terminal:
        raise StartupError(
            "Windows Terminal (wt.exe) is required for direct side-by-side "
            "start.bat. Install Windows Terminal, or in VS Code use "
            "Terminal > Run Task > KATS: Native start (split in VS Code)."
        )
    for entry in (ROOT / "start-frontend.bat", ROOT / "ops" / "launch.bat"):
        if not entry.is_file():
            raise StartupError(f"Cannot launch split terminal: missing {entry}")
    args = windows_terminal_command(terminal)
    try:
        subprocess.Popen(args, cwd=str(ROOT))
    except OSError as exc:
        raise StartupError(f"Cannot open Windows Terminal split panes: {exc}") from exc
    print("[launch] Opened a Windows Terminal window with side-by-side panes:", flush=True)
    print(f"         LEFT: Flask API ({BACKEND_ORIGIN})", flush=True)
    print(f"         RIGHT: React Vite ({FRONTEND_ORIGIN})", flush=True)
    print("         Stop each pane with Ctrl+C; stop.bat preserves local database volumes.", flush=True)
    print("[VS Code] For side-by-side INTEGRATED terminals instead, run task:", flush=True)
    print("          KATS: Native start (split in VS Code)", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Windows KATS launcher")
    parser.add_argument("action", choices=("split", "setup", "doctor", "dev-prepare", "dev-backend", "dev-doctor", "start", "frontend", "backend", "backend-stack", "owner", "stop"))
    action = parser.parse_args().action
    try:
        if os.name != "nt":
            raise StartupError("Windows .bat launcher only. Use Docker on Linux/macOS.")
        if action == "split":
            start_split()
        elif action == "setup":
            settings = config()
            frontend(build=True)
            python = backend()
            mode = select_backend_mode()
            prepare_backend(settings, python, mode)
            print("[setup] Schema and permissions ready (" + mode + " mode).", flush=True)
        elif action == "doctor":
            verify_http_bridge()
        elif action == "dev-prepare":
            dev_prepare()
        elif action == "dev-doctor":
            dev_doctor()
        elif action == "dev-backend":
            os.environ["KATS_DEV_BACKEND"] = "unified"
            os.environ["KATS_FAST_START"] = "1"
            launch("backend-stack")
        elif action == "stop":
            STATE.mkdir(parents=True, exist_ok=True)
            STOP_FILE.write_text(str(time.time()) + "\\n", encoding="utf-8")
            print("[stop] Graceful shutdown requested in all running native terminals.", flush=True)
            # Don't shut down PostgreSQL while the API and workers are draining.
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if not reachable(f"{BACKEND_ORIGIN}/healthz"):
                    break
                time.sleep(0.4)
            if CONFIG.exists() and select_backend_mode() == "docker":
                dependencies(["down"], config())
                print("[stop] PostgreSQL/Redis stopped; volumes retained.", flush=True)
            else:
                print("[stop] SQLite preview database retained in .local.", flush=True)
        elif action == "owner":
            settings = config()
            python = backend()
            mode = select_backend_mode()
            runtime = prepare_backend(settings, python, mode)
            invoke([str(python), "-m", "flask", "--app", "wsgi",
                    "create-user", "--role", "OWNER"],
                   cwd=BACK, env=runtime)
        else:
            launch(action)
        return 0
    except StartupError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130

if __name__ == "__main__":
    raise SystemExit(main())
