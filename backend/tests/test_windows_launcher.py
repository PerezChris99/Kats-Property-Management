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
    vite = (ROOT / "frontend" / "vite.config.js").read_text(encoding="utf-8")
    assert "import ports from '../ops/dev_ports.json'" in vite
    assert "port: frontendPort" in vite
    assert "strictPort: true" in vite
    assert "const backend = `http://127.0.0.1:${backendPort}`" in vite


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
    assert 'launch.bat' in parts[0] and 'backend-stack' in parts[0]
    assert '"'+str(ROOT/"Kats Property Management"/"ops"/"launch.bat")+'"' in parts[0]
    assert 'start-frontend.bat' in parts[1]
    assert 'set "KATS_FAST_START=1"' in (ROOT/"start.bat").read_text(encoding="utf-8")
    assert 'set "KATS_FAST_START=1"' in (ROOT/"start-frontend.bat").read_text(encoding="utf-8")


def test_backend_stack_starts_its_own_celery_worker_beat_and_schedule_directory():
    text=SOURCE.read_text(encoding="utf-8")
    assert 'run_front = mode in ("start", "frontend")' in text
    assert 'run_back = mode in ("start", "backend", "backend-stack")' in text
    assert 'if mode in ("start", "backend-stack") and not preview and backend_mode != "pgdemo":' in text
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


def test_vscode_launches_two_background_services_in_parallel_visible_terminals():
    import json
    import re
    tasks=json.loads((ROOT/".vscode"/"tasks.json").read_text(encoding="utf-8"))["tasks"]
    byname={task["label"]:task for task in tasks}
    master=byname["KATS: Native start (split in VS Code)"]
    assert master["dependsOn"]==["KATS: Start Dev (Frontend + Backend)"]
    top=byname["KATS: Start Dev (Frontend + Backend)"]
    assert top["dependsOrder"]=="parallel"
    assert top["dependsOn"]==[
        "KATS: Unified demo backend (PostgreSQL / SQLite fallback)",
        "KATS: Dev frontend (fast Vite)",
    ]
    front=byname["KATS: Dev frontend (fast Vite)"]
    back=byname["KATS: Unified demo backend (PostgreSQL / SQLite fallback)"]
    assert front["args"][-1]=="dev-frontend"
    assert back["args"][-1]=="dev-backend"
    for task in (front,back):
        assert task["type"]=="process"
        assert task["command"]=="powershell.exe"
        assert task["args"][4].endswith("ops\\vscode_task.ps1")
        matcher=task["problemMatcher"][0]
        assert matcher["background"]["activeOnStart"]
        assert matcher["background"]["endsPattern"]==r"^\[READY\]"
        regex=re.compile(matcher["pattern"]["regexp"])
        assert regex.groups>=3
        assert all(matcher["pattern"][key] in range(1,regex.groups+1)
                   for key in ("file","line","message"))
        assert re.compile(matcher["background"]["endsPattern"]).search("[READY] Flask")
        assert task["isBackground"]
        assert task["presentation"]["panel"]=="dedicated"
        assert task["presentation"]["reveal"]=="always"
    assert front["presentation"]["focus"] is True
    assert back["presentation"]["focus"] is False
    assert front["presentation"]["group"]==back["presentation"]["group"]=="kats-dev-parallel"



def test_vscode_command_palette_daily_start_does_not_depend_on_database_setup():
    import json
    tasks=json.loads((ROOT/".vscode"/"tasks.json").read_text(encoding="utf-8"))["tasks"]
    aliases=[task for task in tasks if task.get("label")=="KATS: Start Dev (Frontend + Backend)"]
    assert len(aliases)==1
    alias=aliases[0]
    assert "type" not in alias
    assert alias["dependsOrder"]=="parallel"
    assert "KATS: Dev prepare (PostgreSQL + seed 31 accounts)" not in alias["dependsOn"]
    assert alias["problemMatcher"]==[]
    assert "flask left" in alias["detail"].lower()
    assert "react right" in alias["detail"].lower()
    initial=next(t for t in tasks if t["label"]=="KATS: Setup demo once + Start Dev")
    assert initial["dependsOrder"]=="sequence"
    assert initial["dependsOn"]==[
        "KATS: Dev prepare (PostgreSQL + seed 31 accounts)",
        alias["label"],
    ]



def test_windows_vscode_tasks_use_argument_safe_process_invocation():
    import json
    tasks=json.loads((ROOT / ".vscode" / "tasks.json").read_text(encoding="utf-8"))["tasks"]
    relevant=[t for t in tasks if t.get("type") == "process"
              and (t.get("label","").startswith("KATS: Native ")
                   or t.get("label","").startswith("KATS Test:"))]
    assert len(relevant)==22
    targets=set()
    for task in relevant:
        assert task["type"]=="process"
        assert task["command"]=="powershell.exe"
        assert task["args"][:4]==["-NoProfile","-ExecutionPolicy","Bypass","-File"]
        assert task["args"][4].endswith(r"\ops\vscode_task.ps1")
        assert task["args"][5]=="-Target"
        assert task["args"][6] not in targets
        targets.add(task["args"][6])
        assert not any("call " in arg for arg in task["args"])
    assert "frontend" in targets and "backend-stack" in targets
    assert "setup" in targets
    assert "test-all" in targets and "test-security" in targets
    script=(ROOT/"ops"/"vscode_task.ps1").read_text(encoding="utf-8")
    assert "[ValidateSet(" in script
    assert "Test-Path -LiteralPath $Batch" in script
    assert "& $Batch @BatchArgs" in script
    assert "exit $Code" in script
    for target in targets:
        assert "'"+target+"' = @{ Script = " in script



def test_missing_docker_uses_isolated_preview_not_production(monkeypatch, tmp_path):
    real_which=launcher.shutil.which
    monkeypatch.setattr(launcher.shutil, "which",
                        lambda name: None if name == "docker" else real_which(name))
    monkeypatch.delenv("KATS_DEV_BACKEND", raising=False)
    assert launcher.select_backend_mode() == "preview"
    monkeypatch.setenv("KATS_DEV_BACKEND", "preview")
    assert launcher.select_backend_mode() == "preview"
    monkeypatch.setenv("KATS_DEV_BACKEND", "docker")
    with pytest.raises(launcher.StartupError, match="Docker"):
        launcher.select_backend_mode()
    monkeypatch.setenv("KATS_DEV_BACKEND", "other")
    with pytest.raises(launcher.StartupError, match="KATS_DEV_BACKEND"):
        launcher.select_backend_mode()


def test_preview_environment_is_local_only_and_never_inherits_live_providers(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "STATE", tmp_path)
    for key, value in {
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql://prod.example/real_money",
        "MTN_MOMO_ENABLED": "true",
        "AIRTEL_MONEY_ENABLED": "true",
        "EFRIS_ENABLED": "true",
        "S3_BUCKET": "real-customer-data",
        "SMTP_HOST": "real-smtp",
    }.items():
        monkeypatch.setenv(key, value)
    settings={"POSTGRES_PASSWORD": "f" * 48, "SECRET_KEY": "a" * 64,
              "JWT_SECRET_KEY": "b" * 64}
    env=launcher.environment(settings, preview=True)
    assert env["APP_ENV"]=="development"
    assert env["DATABASE_URL"]=="sqlite:///" + (tmp_path / "kats-preview.sqlite3").as_posix()
    assert env["REDIS_URL"]=="memory://"
    assert env["RATELIMIT_STORAGE_URI"]=="memory://"
    assert env["CELERY_BROKER_URL"]=="memory://"
    assert env["CELERY_RESULT_BACKEND"]=="cache+memory://"
    assert env["KATS_PREVIEW_MODE"]=="1"
    assert env["CELERY_TASK_ALWAYS_EAGER"]=="true"
    assert not any(env[k]!="false" for k in
                   ("MTN_MOMO_ENABLED","AIRTEL_MONEY_ENABLED","EFRIS_ENABLED"))
    assert "S3_BUCKET" not in env and "SMTP_HOST" not in env
    assert env["DATABASE_URL"]!="postgresql://prod.example/real_money"
    full=launcher.environment(settings)
    assert full["DATABASE_URL"].startswith("postgresql+psycopg://")
    assert "KATS_PREVIEW_MODE" not in full
    assert "CELERY_TASK_ALWAYS_EAGER" not in full


def test_preview_setup_never_calls_docker_or_migrations(monkeypatch, tmp_path):
    monkeypatch.setenv("KATS_SEED_DEMO", "1")
    monkeypatch.setattr(launcher, "STATE", tmp_path)
    commands=[]
    monkeypatch.setattr(launcher, "invoke", lambda args, **kw: commands.append((args,kw)))
    def must_not_touch_docker(*args, **kwargs):
        raise AssertionError("Docker must not run in SQLite preview")
    monkeypatch.setattr(launcher, "dependencies", must_not_touch_docker)
    conf={"POSTGRES_PASSWORD": "f" * 48, "SECRET_KEY": "a" * 64,
          "JWT_SECRET_KEY": "b" * 64}
    env=launcher.prepare_backend(conf, "python-preview", "preview")
    assert env["KATS_PREVIEW_MODE"]=="1"
    assert tmp_path.exists()
    assert len(commands)==3
    # Compare normalized paths rather than assuming Unix separators on Windows.
    assert Path(commands[0][0][-1]).resolve() == (ROOT / "ops" / "init_preview.py").resolve()
    assert commands[0][0][0]=="python-preview"
    assert commands[1][0][-1]=="seed-permissions"
    assert Path(commands[2][0][-1]).resolve() == (ROOT / "ops" / "seed_demo_preview.py").resolve()
    assert not any("upgrade" in command[0] for command in commands)


def test_preview_initializer_has_hardcoded_safe_path_and_env_guards():
    init=(ROOT/"ops"/"init_preview.py").read_text(encoding="utf-8")
    assert 'os.environ.get("APP_ENV") != "development"' in init
    assert 'os.environ.get("KATS_PREVIEW_MODE") != "1"' in init
    assert '"kats-preview.sqlite3"' in init
    assert 'db.create_all()' in init
    assert 'db.drop_all()' not in init
    assert "dbfile.as_posix()" in init


def test_native_tasks_hide_docker_only_commands_and_keep_valid_start_stop():
    import json
    tasks=json.loads((ROOT / ".vscode" / "tasks.json").read_text(encoding="utf-8"))["tasks"]
    by_label={task["label"]:task for task in tasks}
    assert len(by_label)==len(tasks), "Duplicate VS Code task labels"
    for retired in ("KATS: Setup","KATS: Start app","KATS: Logs",
                    "KATS: Full local acceptance"):
        assert retired not in by_label, "Docker-only task is not a native startup"
    assert by_label["KATS: Start Dev (Frontend + Backend)"]["dependsOrder"]=="parallel"
    assert by_label["KATS: Stop (preserve database)"]["args"][-1]=="stop"
    assert by_label["KATS: Native setup (database + build)"]["args"][-1]=="setup"
    assert by_label["KATS: Verify frontend ↔ backend ↔ database"]["args"][-1]=="dev-doctor"
    script=(ROOT / "ops" / "vscode_task.ps1").read_text(encoding="utf-8")
    assert "'start' = @{ Script = 'ops/launch.bat'; Args = @('start') }" in script
