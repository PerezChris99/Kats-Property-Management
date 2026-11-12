"""One-task Windows development launcher: prefer isolated PostgreSQL, fail safely."""
import json
from pathlib import Path
import pytest
from test_windows_launcher import launcher


def configured(monkeypatch, tmp_path, *, postgres):
    monkeypatch.setattr(launcher, "STATE", tmp_path)
    monkeypatch.setattr(launcher, "DEV_MODE_FILE", tmp_path / "dev-mode.json")
    monkeypatch.setattr(launcher, "PG_DEMO_CONFIG", tmp_path / ".env.pg-demo")
    monkeypatch.setattr(launcher, "port_open", lambda port: bool(postgres and port == 5432))
    monkeypatch.setattr(launcher, "frontend", lambda **kwargs: None)
    monkeypatch.setattr(launcher, "backend", lambda: Path("/test-venv/python"))
    monkeypatch.setattr(launcher, "config", lambda: {"POSTGRES_PASSWORD": "test",
        "SECRET_KEY": "unit-test-" * 5, "JWT_SECRET_KEY": "other-unit-test-" * 3})
    monkeypatch.setattr(launcher, "stop_requested", lambda _at: False)
    monkeypatch.setattr(launcher, "venv_environment", lambda env: env)
    calls = []
    monkeypatch.setattr(launcher, "invoke",
                        lambda args, **kwargs: calls.append((list(map(str,args)), kwargs)))
    return calls


def test_postgres_is_the_default_and_31_account_preflight_is_in_one_task(monkeypatch,tmp_path):
    calls = configured(monkeypatch,tmp_path,postgres=True)
    monkeypatch.delenv("KATS_DEMO_DB", raising=False)
    monkeypatch.delenv("KATS_PG_DEMO_PORT", raising=False)
    launcher.dev_prepare()
    status=json.loads((tmp_path/"dev-mode.json").read_text())
    assert status["mode"]=="pgdemo" and status["accounts"]==31
    assert len(calls)==2
    assert calls[0][0][-2:]==["local_postgres_demo.py","prepare"]
    assert calls[1][0][-2:]==["local_postgres_demo.py","check"]
    assert launcher.dev_mode()=="pgdemo"


def test_sqlite_is_a_loud_auto_fallback_only_when_local_pg_is_absent(monkeypatch,tmp_path):
    calls=configured(monkeypatch,tmp_path,postgres=False)
    monkeypatch.delenv("KATS_DEMO_DB", raising=False)
    monkeypatch.delenv("KATS_PG_DEMO_PORT", raising=False)
    launcher.dev_prepare()
    assert launcher.dev_mode()=="preview"
    assert len(calls)==3
    assert any("init_preview.py" in str(cmd) for cmd,_ in calls)
    assert any("seed_demo_preview.py" in str(cmd) for cmd,_ in calls)
    assert any("seed-permissions" in str(cmd) for cmd,_ in calls)


def test_explicit_postgres_fails_closed_without_sqlite_on_unreachable_service(monkeypatch,tmp_path):
    calls=configured(monkeypatch,tmp_path,postgres=False)
    monkeypatch.setenv("KATS_DEMO_DB","postgres")
    with pytest.raises(launcher.StartupError,match="not listening"):
        launcher.dev_prepare()
    assert not calls
    assert not (tmp_path/"dev-mode.json").exists()


def test_wrong_existing_postgres_marker_does_not_fallback(monkeypatch,tmp_path):
    calls=configured(monkeypatch,tmp_path,postgres=True)
    monkeypatch.delenv("KATS_DEMO_DB",raising=False)
    monkeypatch.setattr(launcher,"invoke",lambda *_a,**_kw: (_ for _ in ()).throw(
        launcher.StartupError("Database marker mismatch")))
    with pytest.raises(launcher.StartupError,match="marker mismatch"):
        launcher.dev_prepare()
    assert not (tmp_path/"dev-mode.json").exists()
    assert not calls


def test_never_attach_a_running_backend_to_unknown_database(monkeypatch,tmp_path):
    configured(monkeypatch,tmp_path,postgres=True)
    monkeypatch.setattr(launcher,"port_open",lambda port: port == launcher.BACKEND_PORT)
    with pytest.raises(launcher.StartupError,match="already occupies"):
        launcher.dev_prepare()


def test_unified_backend_requires_successful_local_prepare(monkeypatch,tmp_path):
    configured(monkeypatch,tmp_path,postgres=False)
    with pytest.raises(launcher.StartupError,match="not been prepared"):
        launcher.dev_mode()
    (tmp_path/"dev-mode.json").write_text(json.dumps({
        "mode":"pgdemo","root":"C:/wrong-checkout","accounts":31}))
    with pytest.raises(launcher.StartupError,match="Stale"):
        launcher.dev_mode()


def test_pg_demo_runtime_uses_only_restricted_local_user_and_disables_real_providers(monkeypatch,tmp_path):
    configured(monkeypatch,tmp_path,postgres=True)
    monkeypatch.setattr(launcher,"read_pg_demo_config",lambda:{
        "KATS_DEMO_INSTANCE":"f"*32,
        "KATS_PG_DEMO_PORT":"5432",
        "RUNTIME_PASSWORD":"safe-demo-password-0123456789abcdef",
        "SECRET_KEY":"m"*40, "JWT_SECRET_KEY":"n"*40})
    monkeypatch.setenv("APP_ENV","production")
    monkeypatch.setenv("DATABASE_URL","postgresql://real-host/do-not-connect")
    monkeypatch.setenv("MTN_MOMO_ENABLED","true")
    env=launcher.pg_demo_environment({
        "POSTGRES_PASSWORD":"z"*48,"SECRET_KEY":"a"*40,"JWT_SECRET_KEY":"b"*40
    })
    assert env["DATABASE_URL"].startswith("postgresql+psycopg://kats_demo_runtime:")
    assert env["DATABASE_URL"].endswith("@127.0.0.1:5432/kats_demo")
    assert env["APP_ENV"]=="development"
    assert env["KATS_LOCAL_PG_DEMO"]=="1"
    assert env["KATS_PREVIEW_MODE"]=="0"
    assert env["MTN_MOMO_ENABLED"]=="false"
    assert env["CELERY_TASK_ALWAYS_EAGER"]=="true"
    assert "real-host" not in env["DATABASE_URL"]


def test_vscode_main_task_prepares_then_splits_services_without_additional_process_count():
    root=Path(__file__).resolve().parents[2]
    tasks=json.loads((root/".vscode/tasks.json").read_text())["tasks"]
    by_name={task["label"]:task for task in tasks}
    start=by_name["KATS: Start Dev (Frontend + Backend)"]
    assert start["dependsOrder"]=="sequence"
    assert start["dependsOn"]==[
        "KATS: Dev prepare (PostgreSQL + seed 31 accounts)",
        "KATS: Dev services (split in VS Code)",
    ]
    services=by_name["KATS: Dev services (split in VS Code)"]
    assert services["dependsOrder"]=="parallel"
    assert services["dependsOn"]==[
        "KATS: Unified demo backend (PostgreSQL / SQLite fallback)",
        "KATS: Native frontend (BAT)",
    ]
    assert by_name["KATS: Dev prepare (PostgreSQL + seed 31 accounts)"]["args"][-1]=="dev-prepare"
    assert by_name["KATS: Unified demo backend (PostgreSQL / SQLite fallback)"]["args"][-1]=="dev-backend"
    assert by_name["KATS: Verify frontend ↔ backend ↔ database"]["args"][-1]=="dev-doctor"
    assert by_name["KATS: Native start (split in VS Code)"]["dependsOn"]==[start["label"]]
    assert by_name["KATS: PostgreSQL demo start (31 accounts)"]["dependsOn"]==[start["label"]]
    assert len([t for t in tasks if t.get("type")=="process" and (
        t["label"].startswith("KATS: Native") or t["label"].startswith("KATS Test:"))])==22
