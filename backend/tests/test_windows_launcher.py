"""Cross-platform static and configuration tests for the Windows BAT launcher."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "ops" / "run_windows.py"
spec = spec_from_file_location("native_launcher", SOURCE)
launcher = module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_local_config_created_reused_and_never_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "CONFIG", tmp_path / ".env.native")
    result = launcher.config()
    assert result["KATS_LOCAL_ONLY"] == "1"
    assert result["POSTGRES_DB"] == "kats_native"
    assert result["POSTGRES_USER"] == "kats_native"
    assert len(result["POSTGRES_PASSWORD"]) == 48
    assert len(result["SECRET_KEY"]) == 64
    assert result["SECRET_KEY"] != result["JWT_SECRET_KEY"]
    assert launcher.config() == result


def test_inherited_production_config_cannot_be_used(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "CONFIG", tmp_path / ".env.native")
    conf = launcher.config()
    for key, value in {
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql://real-tenant-db.example/production",
        "MTN_MOMO_ENABLED": "true",
        "AIRTEL_MONEY_ENABLED": "true",
        "EFRIS_ENABLED": "true",
        "S3_BUCKET": "real-customer-bucket",
        "SMTP_HOST": "real-mail-provider.example",
    }.items():
        monkeypatch.setenv(key, value)
    env = launcher.environment(conf)
    assert env["APP_ENV"] == "development"
    assert env["DATABASE_URL"].endswith("@127.0.0.1:55432/kats_native")
    assert env["REDIS_URL"] == "redis://127.0.0.1:56379/0"
    for key in ("MTN_MOMO_ENABLED", "AIRTEL_MONEY_ENABLED", "EFRIS_ENABLED"):
        assert env[key] == "false"
    assert "S3_BUCKET" not in env and "SMTP_HOST" not in env
    assert env["PUBLIC_REGISTRATION_ENABLED"] == "false"


@pytest.mark.parametrize("tamper", (
    "KATS_LOCAL_ONLY=0",
    "POSTGRES_DB=production",
    "POSTGRES_USER=postgres",
    "POSTGRES_PASSWORD=oops",
))
def test_unsafe_native_config_fails_closed(tmp_path, monkeypatch, tamper):
    monkeypatch.setattr(launcher, "CONFIG", tmp_path / ".env.native")
    launcher.config()
    text = launcher.CONFIG.read_text(encoding="utf-8")
    key = tamper.partition("=")[0]
    text = "\n".join(tamper if x.startswith(key + "=") else x
                     for x in text.splitlines()) + "\n"
    launcher.CONFIG.write_text(text, encoding="utf-8")
    with pytest.raises(launcher.StartupError):
        launcher.config()


def test_all_batch_entrypoints_present_and_not_duplicate_action():
    for name, action in (
        ("start.bat", "start"),
        ("start-frontend.bat", "frontend"),
        ("start-backend.bat", "backend"),
        ("create-owner.bat", "owner"),
        ("stop.bat", "stop"),
    ):
        content = (ROOT / name).read_text(encoding="utf-8").lower()
        assert "ops\\launch.bat" in content
        assert f" {action} %*" in content
        assert "%~dp0" in content
    command = (ROOT / "ops" / "launch.bat").read_text(encoding="utf-8")
    assert '"%ACTION%"' in command
    assert '"%ACTION%" %*' not in command


def test_native_db_and_redis_reachable_only_via_localhost():
    compose = (ROOT / "compose.native-deps.yml").read_text(encoding="utf-8")
    assert "127.0.0.1:55432:5432" in compose
    assert "127.0.0.1:56379:6379" in compose
    assert "native_pgdata" in compose
    assert "kats_native" in compose
    assert "8000:" not in compose and "5173:" not in compose
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".local/" in gitignore and ".env.*" in gitignore


def test_launcher_preserves_virtualenv_and_worker_contract():
    source = SOURCE.read_text(encoding="utf-8")
    assert '"APP_ENV": "development"' in source
    assert 'result["VIRTUAL_ENV"]' in source
    assert '"--pool=solo"' in source
    assert '"db", "upgrade"' in source
    assert '"seed-permissions"' in source
    assert "127.0.0.1:8000" in (ROOT / "frontend" / "vite.config.js").read_text(encoding="utf-8")
