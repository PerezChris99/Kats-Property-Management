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
        ("start.bat", "split"),
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


def test_windows_dispatcher_anchors_root_before_argument_handling():
    command = (ROOT / "ops" / "launch.bat").read_text(encoding="utf-8")
    # SHIFT with its default /0 behavior changes %0 to the first argument,
    # so resolving %~dp0 afterward incorrectly picks the parent folder.
    assert not any(line.strip().lower().startswith("shift") for line in command.splitlines())
    assert 'for %%I in ("%~dp0..") do set "KATS_ROOT=%%~fI"' in command
    assert 'set "KATS_SCRIPT=%KATS_ROOT%\\ops\\run_windows.py"' in command
    assert '%PYTHON_CMD% "%KATS_SCRIPT%" "%ACTION%"' in command
    assert 'if not exist "%KATS_SCRIPT%"' in command
    assert '"%KATS_PATH_CHECK_ONLY%"=="1"' in command


def test_split_windows_terminal_command_produces_two_side_by_side_panes():
    content=(ROOT/"start.bat").read_text(encoding="utf-8")
    assert 'ops\\launch.bat" split %*' in content
    cmd=launcher.windows_terminal_command("wt.exe",ROOT/"Kats Property Management")
    assert cmd[:3]==["wt.exe","-w","new"]
    assert cmd.count("new-tab")==1
    assert cmd.count("split-pane")==1
    assert cmd[cmd.index("split-pane")+1]=="-V"
    assert cmd.count("--title")==2 and cmd.count("--startingDirectory")==2
    parts=[cmd[i+1] for i,x in enumerate(cmd[:-1]) if x=="/k"]
    assert len(parts)==2
    assert 'start-frontend.bat' in parts[0]
    assert '"'+str(ROOT/"Kats Property Management"/"start-frontend.bat")+'"' in parts[0]
    assert 'launch.bat' in parts[1] and 'backend-stack' in parts[1]


def test_backend_stack_starts_its_own_celery_worker_beat_and_schedule_directory():
    text=SOURCE.read_text(encoding="utf-8")
    assert 'run_front = mode in ("start", "frontend")' in text
    assert 'run_back = mode in ("start", "backend", "backend-stack")' in text
    assert 'if mode in ("start", "backend-stack"):' in text
    assert 'STATE.mkdir(parents=True, exist_ok=True)' in text
    assert 'if action == "split":' in text
    assert 'start_split()' in text


def test_concurrent_frontend_backend_share_complete_config(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setattr(launcher,"CONFIG",tmp_path/".env.native")
    with ThreadPoolExecutor(max_workers=10) as pool:
        configs=list(pool.map(lambda _: launcher.config(),range(20)))
    assert all(data==configs[0] for data in configs)
    assert len(configs[0]["SECRET_KEY"])==64
    assert len(configs[0]["JWT_SECRET_KEY"])==64
    assert not list(tmp_path.glob(".env.native.*.tmp"))


def test_vscode_uses_parallel_background_tasks_in_one_split_terminal_group():
    import json
    tasks=json.loads((ROOT/".vscode"/"tasks.json").read_text(encoding="utf-8"))["tasks"]
    byname={task["label"]:task for task in tasks}
    master=byname["KATS: Native start (split in VS Code)"]
    assert master["dependsOrder"]=="parallel"
    assert master["dependsOn"]==["KATS: Native frontend (BAT)","KATS: Native backend stack (BAT)"]
    front=byname["KATS: Native frontend (BAT)"]
    back=byname["KATS: Native backend stack (BAT)"]
    assert "start-frontend.bat" in front["args"][-1]
    assert "backend-stack" in back["args"][-1]
    assert front["isBackground"] and back["isBackground"]
    assert front["presentation"]["group"]==back["presentation"]["group"]=="kats-native-split"
    assert front["presentation"]["panel"]==back["presentation"]["panel"]=="dedicated"


def test_vscode_command_palette_start_dev_entry_is_discoverable():
    import json
    tasks=json.loads((ROOT/".vscode"/"tasks.json").read_text(encoding="utf-8"))["tasks"]
    aliases=[task for task in tasks if task.get("label")=="KATS: Start Dev (Frontend + Backend)"]
    assert len(aliases)==1
    alias=aliases[0]
    assert alias["dependsOrder"]=="parallel"
    assert alias["dependsOn"]==["KATS: Native frontend (BAT)","KATS: Native backend stack (BAT)"]
    assert alias["problemMatcher"]==[]
    assert all(task.get("label") in {t["label"] for t in tasks} for task in (
        {"label":"KATS: Native frontend (BAT)"},{"label":"KATS: Native backend stack (BAT)"}
    ))
    assert alias["detail"].lower().find("side by side")!=-1
