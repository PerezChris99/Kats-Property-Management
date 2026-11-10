"""Safety and dispatch checks for Windows testing .bat files."""
import importlib.util
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("kats_test_runner", ROOT / "ops" / "test_windows.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

EXPECTED = {
    "test-all.bat":"all", "test-frontend.bat":"frontend",
    "test-frontend-unit.bat":"frontend-unit", "test-lint.bat":"lint",
    "test-build.bat":"build", "test-backend.bat":"backend",
    "test-api.bat":"api", "test-security.bat":"security",
    "test-database.bat":"database", "test-migrations.bat":"migrations",
    "test-performance.bat":"performance", "test-e2e.bat":"e2e",
    "test-smoke.bat":"smoke", "test-config.bat":"config",
    "test-coverage.bat":"coverage", "test-load.bat":"load",
}

def test_all_batch_types_have_correct_dispatch_and_error_propagation():
    assert set(EXPECTED.values()) == set(runner.ACTIONS)
    dispatcher = (ROOT / "ops" / "tests.bat").read_text(encoding="utf-8")
    assert '"%ACTION%"' in dispatcher
    assert '"%ACTION%" %*' not in dispatcher
    for filename, action in EXPECTED.items():
        content = (ROOT / filename).read_text(encoding="utf-8")
        assert 'call "%~dp0ops\\tests.bat" '+action in content
        assert "exit /b %ERRORLEVEL%" in content

def test_master_runs_all_suites_and_excludes_unapproved_staging(monkeypatch, capsys):
    called=[]
    monkeypatch.setattr(runner, "perform", called.append)
    monkeypatch.setattr(sys, "argv", ["test_windows.py", "all"])
    assert runner.main() == 0
    assert called == ["config","frontend","coverage","database","e2e"]
    assert "Staging-only k6 load" in capsys.readouterr().out

def test_master_accumulates_failures_and_returns_nonzero(monkeypatch):
    called=[]
    def perform(name):
        called.append(name)
        if name=="frontend":
            raise runner.Failed("simulated build error")
    monkeypatch.setattr(runner,"perform",perform)
    monkeypatch.setattr(sys,"argv",["test_windows.py","all"])
    assert runner.main()==1
    assert called==["config","frontend","coverage","database","e2e"]

def test_test_env_never_uses_inherited_production_credentials(monkeypatch):
    values={
        "APP_ENV":"production",
        "DATABASE_URL":"postgresql://business.example/production",
        "TEST_POSTGRES_URL":"postgresql://business.example/production",
        "MTN_MOMO_ENABLED":"true", "AIRTEL_MONEY_ENABLED":"true",
        "EFRIS_ENABLED":"true", "S3_BUCKET":"secret-data", "SMTP_HOST":"mail.example",
    }
    for key,value in values.items(): monkeypatch.setenv(key,value)
    env=runner.test_env()
    assert env["APP_ENV"]=="testing" and env["DATABASE_URL"]=="sqlite:///:memory:"
    assert "TEST_POSTGRES_URL" not in env
    assert "S3_BUCKET" not in env and "SMTP_HOST" not in env
    for key in ("MTN_MOMO_ENABLED","AIRTEL_MONEY_ENABLED","EFRIS_ENABLED"):
        assert env[key]=="false"

def test_postgres_compose_is_disposable_and_never_uses_operational_volume():
    source=(ROOT/"compose.verification.yml").read_text(encoding="utf-8")
    assert "test-db:" in source and "kats_ci" in source
    assert "kats-verification" in source and "tmpfs:" in source
    assert "postgres_data:" not in source and "ports:" not in source
    assert "docker-compose.yml" not in source
    assert "test_postgres_invariants.py" in (ROOT/"ops"/"test_windows.py").read_text(encoding="utf-8")

@pytest.mark.parametrize("url",("https://production.example","http://192.168.0.3:5173","http://localhost:8000"))
def test_smoke_rejects_nonlocal_urls(monkeypatch,url):
    monkeypatch.setenv("KATS_SMOKE_URL",url)
    with pytest.raises(runner.Failed):
        runner.smoke()

def test_load_does_nothing_without_explicit_approval(monkeypatch):
    monkeypatch.delenv("KATS_LOAD_TEST_APPROVED",raising=False)
    monkeypatch.delenv("BASE_URL",raising=False)
    with pytest.raises(runner.Failed):
        runner.load()


def test_static_config_forces_sample_env_file_not_business_config():
    source=(ROOT/"ops"/"test_windows.py").read_text(encoding="utf-8")
    assert 'KATS_ENV_FILE="ops/production.env.sample"' in source
    assert '"nginx:stable-alpine","nginx","-t"' in source
    assert '"caddy:2-alpine","caddy","validate"' in source
