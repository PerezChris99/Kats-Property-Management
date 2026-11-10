"""Windows KATS test runner (called by test-*.bat from CMD or PowerShell).

No production database access: PostgreSQL tests use independent kats_ci tmpfs;
E2E uses disposable kats_e2e; load testing requires explicit approved staging.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
BACK = ROOT / "backend"
FRONT = ROOT / "frontend"
VENV = ROOT / ".venv" / "Scripts" / "python.exe"
PG_PROJECT = "kats-verification"
PG_COMPOSE = ROOT / "compose.verification.yml"

API = ("test_api_authorization_surface.py", "test_workflows.py",
       "test_sessions.py", "test_permission_matrix.py", "test_health.py")
SECURITY = ("test_security_hardening.py", "test_api_authorization_surface.py",
            "test_permission_matrix.py", "test_sessions.py", "test_mfa.py",
            "test_production_config.py", "test_malware_scan.py",
            "test_account_recovery.py")
PERFORMANCE = ("test_billing_batch_performance.py",
               "test_maintenance_batch_performance.py")
ACTIONS = ("all", "frontend", "frontend-unit", "lint", "build", "backend",
           "api", "security", "database", "migrations", "performance",
           "e2e", "smoke", "config", "coverage", "load")

class Failed(RuntimeError):
    pass

def need(name):
    executable = shutil.which(name)
    if not executable:
        raise Failed(f"{name} unavailable. Install it and reopen VS Code.")
    return executable

def exec_cmd(args, *, cwd=ROOT, env=None):
    result = subprocess.run(args, cwd=str(cwd), env=env, check=False)
    if result.returncode:
        raise Failed(f"{Path(args[0]).name}: exit {result.returncode}")

def test_env():
    env = os.environ.copy()
    env.update(APP_ENV="testing", DATABASE_URL="sqlite:///:memory:",
               RATELIMIT_STORAGE_URI="memory://", RATELIMIT_ENABLED="false",
               MTN_MOMO_ENABLED="false", AIRTEL_MONEY_ENABLED="false",
               EFRIS_ENABLED="false", EMAIL_PROVIDER_ENABLED="false",
               SMS_PROVIDER_ENABLED="false", PUBLIC_REGISTRATION_ENABLED="false")
    for key in ("TEST_POSTGRES_URL", "TEST_DOCUMENT_RLS_URL", "S3_BUCKET",
                "S3_ENDPOINT_URL", "SMTP_HOST", "SMTP_PASSWORD",
                "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        env.pop(key, None)
    return env

_python_ready = False
_npm_ready = False

def python():
    global _python_ready
    if not _python_ready:
        if sys.version_info < (3,12):
            raise Failed("Python 3.12 or newer is required.")
        if not VENV.is_file():
            exec_cmd([sys.executable, "-m", "venv", str(VENV.parent.parent)])
        check = subprocess.run([str(VENV), "-c",
                                "import sys;assert sys.version_info>=(3,12)"],
                               capture_output=True, check=False)
        if check.returncode:
            raise Failed("Project .venv uses incompatible Python. Recreate it.")
        exec_cmd([str(VENV), "-m", "pip", "install", "-r",
                  str(BACK / "requirements.txt")], env=test_env())
        _python_ready = True
    return str(VENV)

def npm():
    global _npm_ready
    binary = need("npm.cmd" if os.name=="nt" else "npm")
    node = need("node")
    result = subprocess.run([node, "-p", "process.versions.node.split('.')[0]"],
                            capture_output=True, text=True, check=False)
    if result.returncode or not result.stdout.strip().isdigit() or int(result.stdout.strip())<22:
        raise Failed("Node 22 or newer required.")
    if not _npm_ready:
        exec_cmd([binary, "ci", "--no-audit", "--no-fund"], cwd=FRONT)
        _npm_ready = True
    return binary

def pytest(names=(), coverage=False):
    py = python()
    args = [py, "-m", "pytest", "-q"]
    if coverage:
        (ROOT / ".local").mkdir(exist_ok=True)
        exec_cmd([py, "-m", "pip", "install", "pytest-cov>=5,<7"], env=test_env())
        args += ["--cov=app", "--cov-report=term-missing",
                 "--cov-report=xml:" + str(ROOT / ".local" / "coverage.xml")]
    args += [str(BACK / "tests" / name) for name in names]
    exec_cmd(args, cwd=BACK, env=test_env())

def frontend(action):
    scripts = {"frontend":("build",), "frontend-unit":("test",),
               "lint":("check:jsx","lint"), "build":("build",)}
    cli = npm()
    for script in scripts[action]:
        exec_cmd([cli, "run", script], cwd=FRONT)

def compose(args):
    exec_cmd([need("docker"), "compose", "-p", PG_PROJECT,
              "-f", str(PG_COMPOSE)] + args)

def postgres(migrations_only=False):
    compose(["config","--quiet"])
    try:
        compose(["up","-d","--wait","test-db"])
        checks = ["python -m flask --app wsgi db upgrade",
                  "python -m flask --app wsgi db downgrade base",
                  "python -m flask --app wsgi db upgrade"]
        if not migrations_only:
            checks.extend(("python tests/prepare_postgres.py",
                "python -m pytest -q tests/test_postgres_invariants.py tests/test_postgres_document_rls.py"))
        compose(["run","--rm","-T","verifier","sh","-ec"," && ".join(checks)])
    finally:
        # This Compose file has a disposable tmpfs DB and no production services.
        compose(["down","--remove-orphans"])

def config():
    py=python()
    exec_cmd([py,"ops/check-secrets.py"])
    exec_cmd([py,"-m","compileall","-q","backend/app","ops"])
    for path in (".vscode/tasks.json",".vscode/extensions.json","frontend/package.json"):
        with (ROOT/path).open(encoding="utf-8") as source:
            json.load(source)
    env=os.environ.copy()
    env.update(POSTGRES_PASSWORD="dummy_native_only",
               KATS_E2E_SECRET_KEY=secrets.token_hex(32),
               KATS_E2E_JWT_SECRET_KEY=secrets.token_hex(32))
    docker=need("docker")
    for path in ("compose.verification.yml","compose.native-deps.yml","compose.e2e.yml"):
        exec_cmd([docker,"compose","-f",str(ROOT/path),"config","--quiet"],env=env)
    exec_cmd([docker,"compose","--env-file","ops/production.env.sample",
              "-f","compose.production.yml","config","--quiet"],env=env)

def smoke():
    base=os.environ.get("KATS_SMOKE_URL","http://127.0.0.1:5173").rstrip("/")
    if base not in ("http://127.0.0.1:5173","http://localhost:5173",
                    "http://127.0.0.1:5174","http://localhost:5174"):
        raise Failed("Smoke targets must be localhost:5173 or localhost:5174")
    for path,status in (("/",200),("/healthz",200),("/readyz",200),
                        ("/api/v1/public/landing-content",200),
                        ("/api/v1/properties",401)):
        try:
            with urllib.request.urlopen(base+path,timeout=15) as r:
                code=r.status
        except urllib.error.HTTPError as e:
            code=e.code
        except OSError as e:
            raise Failed(f"Start the local application before smoke testing: {e}") from e
        if code!=status:
            raise Failed(f"{path}: expected {status}, returned {code}")

def browser():
    need("docker")
    shell=shutil.which("powershell.exe") or shutil.which("powershell")
    if not shell:
        raise Failed("Windows PowerShell required for six-role browser suite")
    # Existing isolated E2E runner generates test users and tears down test DB.
    exec_cmd([shell,"-NoProfile","-ExecutionPolicy","Bypass",
              "-File",str(ROOT/"ops"/"dev.ps1"),
              "-Action","browser-full"],env=test_env())

def load():
    if os.environ.get("KATS_LOAD_TEST_APPROVED")!="yes" or not os.environ.get("BASE_URL"):
        raise Failed("Staging k6 requires KATS_LOAD_TEST_APPROVED=yes and BASE_URL=https://approved-staging-host; no request sent.")
    exec_cmd([need("k6"),"run","ops/load-test.js"])

def perform(action):
    if action in ("frontend","frontend-unit","lint","build"):
        frontend(action)
    elif action=="backend":
        pytest()
    elif action=="api":
        pytest(API)
    elif action=="security":
        exec_cmd([python(),"ops/check-secrets.py"])
        pytest(SECURITY)
    elif action=="performance":
        pytest(PERFORMANCE)
    elif action=="coverage":
        pytest(coverage=True)
    elif action in ("database","migrations"):
        postgres(migrations_only=(action=="migrations"))
    elif action=="config":
        config()
    elif action=="e2e":
        browser()
    elif action=="smoke":
        smoke()
    elif action=="load":
        load()
    else:
        raise Failed("Unsupported test action")

def main():
    parser=argparse.ArgumentParser(description="KATS automated test suites")
    parser.add_argument("action",choices=ACTIONS)
    action=parser.parse_args().action
    if action!="all":
        try:
            print(f"[KATS] Starting {action}",flush=True)
            perform(action)
            print(f"[PASS] {action}",flush=True)
            return 0
        except (Failed,OSError,subprocess.SubprocessError) as e:
            print(f"[FAIL] {action}: {e}",file=sys.stderr,flush=True)
            return 1
    # Every locally runnable test: complete Python pytest includes API,
    # security, scheduler-performance tests; frontend build includes JSX/lint/JS.
    results={}
    for name in ("config","frontend","backend","database","e2e"):
        print(f"\n===== KATS TEST: {name.upper()} =====",flush=True)
        try:
            perform(name)
            results[name]="PASS"
        except (Failed,OSError,subprocess.SubprocessError) as e:
            results[name]="FAIL"
            print(f"[FAIL] {name}: {e}",file=sys.stderr,flush=True)
    print("\n===== KATS FULL LOCAL SUITE =====")
    for name,status in results.items():
        print(f"{name:12} {status}")
    print("Smoke and role checks are included in isolated E2E.")
    print("API, security and performance tests are included in backend pytest.")
    print("Staging-only k6 load and human/third-party acceptance: NOT RUN.")
    return int(any(status!="PASS" for status in results.values()))

if __name__=="__main__":
    raise SystemExit(main())
