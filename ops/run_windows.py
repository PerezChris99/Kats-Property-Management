"""Native Windows development launcher invoked by root .bat scripts.

Starts React, Flask, Celery solo worker, and Celery beat in ONE integrated
CMD or PowerShell terminal. Docker runs only a dedicated Postgres/Redis pair.
No operational .env or database is read or modified.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
FRONT = ROOT / "frontend"
BACK = ROOT / "backend"
STATE = ROOT / ".local"
VENV = ROOT / ".venv"
CONFIG = ROOT / ".env.native"
COMPOSE = ROOT / "compose.native-deps.yml"
PROJECT = "kats-native"

class StartupError(RuntimeError):
    pass

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

def environment(settings):
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
        "CORS_ORIGINS": "http://localhost:5173,http://127.0.0.1:5173",
        "PUBLIC_APP_URL": "http://localhost:5173",
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
    return values

def frontend():
    node, npm = require("node"), require("npm.cmd")
    major = subprocess.run([node, "-p", "process.versions.node.split('.')[0]"],
                           capture_output=True, text=True, check=False)
    if major.returncode or not major.stdout.strip().isdigit() or int(major.stdout.strip()) < 22:
        raise StartupError("Node.js 22 or newer is required.")
    STATE.mkdir(exist_ok=True)
    lock = FRONT / "package-lock.json"
    stamp = STATE / "npm-lock.sha256"
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    if (not (FRONT / "node_modules").is_dir()
        or not stamp.exists() or stamp.read_text(encoding="utf-8") != digest):
        print("[frontend] Installing npm packages...", flush=True)
        invoke([npm, "ci", "--no-audit", "--no-fund"], cwd=FRONT)
        stamp.write_text(digest, encoding="utf-8")
    print("[frontend] Verifying JSX, linting, testing and building React...", flush=True)
    invoke([npm, "run", "build"], cwd=FRONT)
    return npm

def backend():
    if sys.version_info < (3, 12):
        raise StartupError("Python 3.12+ is required.")
    python = VENV / "Scripts" / "python.exe"
    active = bool(os.environ.get("VIRTUAL_ENV") and
                  os.path.normcase(os.path.abspath(os.environ["VIRTUAL_ENV"]))
                  == os.path.normcase(str(VENV.resolve())))
    if not python.is_file():
        print("[backend] Creating .venv...", flush=True)
        invoke([sys.executable, "-m", "venv", str(VENV)])
    probe = subprocess.run([str(python), "-c",
                            "import sys; assert sys.version_info >= (3,12)"],
                           capture_output=True, check=False)
    if probe.returncode:
        raise StartupError("Existing project .venv uses unsupported Python; recreate it.")
    print("[backend] " + ("Project .venv already active." if active
                          else "Activating project .venv for backend processes."), flush=True)
    print("[backend] Installing required pip packages...", flush=True)
    invoke([str(python), "-m", "pip", "install", "-r", str(BACK / "requirements.txt")])
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

def check_port(port):
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise StartupError(f"Port {port} is in use; stop the other local app or Docker stack.")

def reachable(url):
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            return response.status == 200
    except OSError:
        return False

def kill_tree(process):
    if process.poll() is None:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

def launch(mode):
    settings = config()
    base = environment(settings)
    run_front = mode in ("start", "frontend")
    run_back = mode in ("start", "backend", "backend-stack")
    if run_front:
        check_port(5173)
    if run_back:
        check_port(8000)
    npm = frontend() if run_front else None
    python = backend() if run_back else None
    runtime = venv_environment(base)
    if run_back:
        print("[dependencies] Starting dedicated PostgreSQL + Redis in Docker...", flush=True)
        dependencies(["up", "-d", "--wait"], settings)
        print("[backend] Running Alembic migrations and permission seeding...", flush=True)
        invoke([str(python), "-m", "flask", "--app", "wsgi", "db", "upgrade"],
               cwd=BACK, env=runtime)
        invoke([str(python), "-m", "flask", "--app", "wsgi", "seed-permissions"],
               cwd=BACK, env=runtime)
    processes = []
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        if run_front:
            processes.append(("React", subprocess.Popen(
                [npm, "run", "dev", "--", "--host", "127.0.0.1", "--strictPort"],
                cwd=str(FRONT), env=base, creationflags=flags)))
        if run_back:
            processes.append(("Flask", subprocess.Popen(
                [str(python), "-m", "flask", "--app", "wsgi", "run",
                 "--host", "127.0.0.1", "--port", "8000", "--no-reload"],
                cwd=str(BACK), env=runtime, creationflags=flags)))
            if mode in ("start", "backend-stack"):
                STATE.mkdir(parents=True, exist_ok=True)
                # Windows Celery workers must use the solo pool, not prefork.
                processes.append(("Celery worker", subprocess.Popen(
                    [str(python), "-m", "celery", "-A", "app.tasks.celery_app",
                     "worker", "--pool=solo", "--loglevel=warning"],
                    cwd=str(BACK), env=runtime, creationflags=flags)))
                processes.append(("Celery beat", subprocess.Popen(
                    [str(python), "-m", "celery", "-A", "app.tasks.celery_app",
                     "beat", "--loglevel=warning",
                     "--schedule", str(STATE / "celerybeat-schedule")],
                    cwd=str(BACK), env=runtime, creationflags=flags)))
        until = time.monotonic() + 45
        while time.monotonic() < until:
            for name, proc in processes:
                if proc.poll() is not None:
                    raise StartupError(f"{name} exited early (exit {proc.returncode}).")
            if ((not run_front or reachable("http://127.0.0.1:5173/"))
                and (not run_back or reachable("http://127.0.0.1:8000/readyz"))):
                break
            time.sleep(.5)
        else:
            raise StartupError("Service readiness timed out; inspect startup errors above.")
        print("\n[READY] React http://localhost:5173 | Flask http://localhost:8000", flush=True)
        print("[READY] Press Ctrl+C here to stop all application processes.", flush=True)
        while True:
            for name, proc in processes:
                if proc.poll() is not None:
                    raise StartupError(f"{name} exited (code {proc.returncode}).")
            time.sleep(.5)
    except KeyboardInterrupt:
        print("\n[stop] Stopping all launched services...", flush=True)
    finally:
        for _, proc in reversed(processes):
            kill_tree(proc)
        # DB/Redis persist for subsequent runs; stop.bat stops containers.

def windows_terminal_command(executable, root=ROOT):
    """Build two side-by-side panes in ONE Windows Terminal window.

    Each pane has an independent process, exit status and Ctrl+C handler.
    -V creates a vertical divider (left/right), not an upper/lower split.
    """
    root = Path(root)
    frontend_batch = root / "start-frontend.bat"
    backend_batch = root / "ops" / "launch.bat"
    return [
        str(executable), "-w", "new",
        "new-tab", "--startingDirectory", str(root),
        "--title", "KATS Frontend",
        "cmd.exe", "/k", f'call "{frontend_batch}"',
        ";",
        "split-pane", "-V", "--startingDirectory", str(root),
        "--title", "KATS Backend + Celery",
        "cmd.exe", "/k", f'call "{backend_batch}" backend-stack',
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
    print("         LEFT: React (http://localhost:5173)", flush=True)
    print("         RIGHT: Flask + Celery worker + Celery beat (http://localhost:8000)", flush=True)
    print("         Stop each pane with Ctrl+C; stop.bat preserves local database volumes.", flush=True)
    print("[VS Code] For side-by-side INTEGRATED terminals instead, run task:", flush=True)
    print("          KATS: Native start (split in VS Code)", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Windows KATS launcher")
    parser.add_argument("action", choices=("split", "start", "frontend", "backend", "backend-stack", "owner", "stop"))
    action = parser.parse_args().action
    try:
        if os.name != "nt":
            raise StartupError("Windows .bat launcher only. Use Docker on Linux/macOS.")
        if action == "split":
            start_split()
        elif action == "stop":
            if CONFIG.exists():
                dependencies(["down"], config())
            print("[stop] PostgreSQL/Redis stopped, volumes retained.")
        elif action == "owner":
            settings = config()
            python = backend()
            dependencies(["up", "-d", "--wait"], settings)
            invoke([str(python), "-m", "flask", "--app", "wsgi",
                    "create-user", "--role", "OWNER"],
                   cwd=BACK, env=venv_environment(environment(settings)))
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
