"""Native lifecycle regression checks for frontend logs, proxy and shutdown."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import io
import json
import os
import time
import urllib.error
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = spec_from_file_location("native_lifecycle", ROOT / "ops" / "run_windows.py")
native = module_from_spec(spec)
spec.loader.exec_module(native)


def test_live_frontend_logs_are_printed_in_terminal(capsys):
    proc = SimpleNamespace(stdout=io.StringIO("VITE ready on port 5173\nHMR updated\n"))
    native.stream_logs("React", proc)
    output = capsys.readouterr().out
    assert "[React] VITE ready on port 5173" in output
    assert "[React] HMR updated" in output


def test_graceful_shutdown_avoids_force_kill_when_child_exits(monkeypatch):
    class GracefulProc:
        pid = 1234
        stopped = False
        def poll(self): return 0 if self.stopped else None
        def terminate(self): self.stopped = True
        def send_signal(self, _signal): self.stopped = True
        def wait(self, timeout=None):
            assert timeout is not None
            return 0
    process = GracefulProc()
    monkeypatch.setattr(native.subprocess, "run",
                        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("forced taskkill")))
    native.kill_tree(process)
    assert process.stopped


def test_stop_marker_is_newer_than_process_start(monkeypatch, tmp_path):
    marker = tmp_path / "stop-request"
    monkeypatch.setattr(native, "STOP_FILE", marker)
    assert native.stop_requested(time.time()) is False
    marker.write_text("shutdown", encoding="utf-8")
    assert native.stop_requested(time.time() - 5) is True
    assert native.stop_requested(time.time() + 5) is False


def test_html_spa_fallback_is_never_backend_ready(monkeypatch):
    class HtmlResponse:
        status = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def read(self): return b"<!doctype html><html><body>Vite</body></html>"
    monkeypatch.setattr(native.urllib.request, "urlopen",
                        lambda *_args, **_kw: HtmlResponse())
    with pytest.raises(native.StartupError, match="connection check failed"):
        native.verify_http_bridge()


def test_full_proxy_auth_db_handshake_passes(monkeypatch, capsys):
    class JsonResponse:
        status = 200
        headers = {"X-Request-ID": "local-ci-id"}
        def __init__(self, content): self.content = content
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def read(self): return json.dumps(self.content).encode()
    def fake_urlopen(url, timeout):
        if url.endswith("/readyz"):
            return JsonResponse({"status": "ready"})
        if url.endswith("/api/v1/auth/me"):
            raise urllib.error.HTTPError(url, 401, "Unauthorized",
                                         {"X-Request-ID": "local-ci-id"}, None)
        raise AssertionError("Unexpected network check")
    monkeypatch.setattr(native.urllib.request, "urlopen", fake_urlopen)
    native.verify_http_bridge()
    assert "[CONNECTED]" in capsys.readouterr().out


def test_auto_docker_selection_requires_running_daemon(monkeypatch):
    monkeypatch.setenv("KATS_DEV_BACKEND", "auto")
    monkeypatch.setattr(native.shutil, "which", lambda n: "docker.exe" if n == "docker" else None)
    monkeypatch.setattr(native.subprocess, "run",
                        lambda *args, **kw: SimpleNamespace(returncode=1))
    assert native.select_backend_mode() == "preview"
    monkeypatch.setenv("KATS_DEV_BACKEND", "docker")
    with pytest.raises(native.StartupError, match="Docker"):
        native.select_backend_mode()


def test_parallel_start_detects_both_backends_without_start_order_assumption():
    source = (ROOT / "ops" / "run_windows.py").read_text(encoding="utf-8")
    assert 'connected = False' in source
    assert 'and reachable(f"{FRONTEND_ORIGIN}/")' in source
    assert 'and reachable(f"{BACKEND_ORIGIN}/readyz")' in source
    assert 'verify_http_bridge()' in source


def test_frontend_start_skips_release_build_and_installed_packages(tmp_path, monkeypatch):
    front=tmp_path/"frontend"
    vite=front/"node_modules"/"vite"/"bin"/"vite.js"
    vite.parent.mkdir(parents=True)
    vite.write_text("/* mock */", encoding="utf-8")
    (front/"package-lock.json").write_text("lock-v1", encoding="utf-8")
    monkeypatch.setattr(native, "FRONT", front)
    monkeypatch.setattr(native, "STATE", tmp_path/"state")
    monkeypatch.setattr(native, "require", lambda name: name)
    calls=[]
    monkeypatch.setattr(native.subprocess, "run",
                        lambda *args, **kw: SimpleNamespace(returncode=0, stdout="22"))
    monkeypatch.setattr(native, "invoke",
                        lambda argv, **kw: calls.append(argv))
    native.frontend(build=False)
    assert any("ci" in command for command in calls)
    assert not any("build" in command for command in calls)
    calls.clear()
    native.frontend(build=False)
    assert calls==[], "Repeated Vite startup must not reinstall or rebuild"
    native.frontend(build=True)
    assert any(command[-1]=="build" for command in calls)
    calls.clear()
    (front/"package-lock.json").write_text("lock-v2", encoding="utf-8")
    native.frontend(build=False)
    assert any("ci" in command for command in calls), "Changed lockfile must reinstall"


def test_backend_start_skips_pip_if_existing_project_packages_are_healthy(tmp_path, monkeypatch):
    venv=tmp_path/"venv"
    exe=venv/"Scripts"/"python.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"mock python executable")
    back=tmp_path/"backend"
    back.mkdir()
    requirements=back/"requirements.txt"
    requirements.write_text("Flask>=3.1,<4\\n", encoding="utf-8")
    monkeypatch.setattr(native, "VENV", venv)
    monkeypatch.setattr(native, "BACK", back)
    monkeypatch.setattr(native, "STATE", tmp_path/"state")
    calls=[]
    monkeypatch.setattr(native, "invoke",lambda argv,**kw: calls.append(argv))
    monkeypatch.setattr(native.subprocess,"run",
                        lambda *_args, **_kw: SimpleNamespace(returncode=0))
    native.backend()
    native.backend()
    assert not calls, "Existing healthy environments must not invoke pip"
    requirements.write_text("Flask>=3.1,<4\\nredis>=5,<7\\n",encoding="utf-8")
    native.backend()
    assert any("install" in args for args in calls), "Changed requirements must invoke pip"


def test_existing_kats_backend_is_reused_and_foreign_port_is_rejected(monkeypatch, capsys):
    """An existing KATS API does not block the Vite frontend from starting."""
    monkeypatch.setattr(native, "port_open", lambda port: port == 8000)

    class Response:
        status = 200
        headers = {"X-Request-ID": "request-123"}
        def __init__(self, payload):
            self.payload = payload
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            pass
        def read(self, *_args):
            return self.payload

    def valid_backend(url, timeout):
        if url.endswith("/readyz"):
            return Response(b'{"status":"ready"}')
        if url.endswith("/api/v1/auth/me"):
            raise urllib.error.HTTPError(
                url, 401, "Unauthorized", {"X-Request-ID": "request-123"}, None
            )
        raise AssertionError("Wrong backend route")

    monkeypatch.setattr(native.urllib.request, "urlopen", valid_backend)
    assert native.existing_kats_service("backend") is True
    assert native.existing_kats_service("frontend") is False
    assert "[reuse] Existing KATS backend" in capsys.readouterr().out

    def foreign_backend(url, timeout):
        return Response(b"<html>Another application</html>")
    monkeypatch.setattr(native.urllib.request, "urlopen", foreign_backend)
    with pytest.raises(native.StartupError, match="Port 8000 is occupied"):
        native.existing_kats_service("backend")


def test_existing_kats_frontend_is_recognized_by_page_signature(monkeypatch):
    monkeypatch.setattr(native, "port_open", lambda port: port == 5173)

    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            pass
        def read(self, *_args):
            return b'<!doctype html><title>KATS property management</title><script src="/src/main.jsx"></script>'
    monkeypatch.setattr(native.urllib.request, "urlopen",
                        lambda *_args, **_kwargs: Response())
    assert native.existing_kats_service("frontend")


def test_combined_launch_starts_missing_react_when_flask_already_running(monkeypatch, capsys):
    started = []
    stopped = []
    monkeypatch.setattr(native, "config", lambda: {"KATS_LOCAL_ONLY": "1"})
    monkeypatch.setattr(native, "environment", lambda settings: {})
    monkeypatch.setattr(native, "select_backend_mode", lambda: "preview")
    monkeypatch.setattr(native, "existing_kats_service",
                        lambda kind: kind == "backend")
    monkeypatch.setattr(native, "frontend", lambda **kwargs: started.append("prepare React"))
    monkeypatch.setattr(native, "backend",
                        lambda: (_ for _ in ()).throw(AssertionError("Flask already running")))
    monkeypatch.setattr(native, "prepare_backend",
                        lambda *_args: (_ for _ in ()).throw(AssertionError("Must not rebuild DB")))
    monkeypatch.setattr(native, "require", lambda name: "node.exe")
    monkeypatch.setattr(native, "reachable", lambda url: True)
    checks = iter((False, True))
    monkeypatch.setattr(native, "stop_requested", lambda *_args: next(checks))
    monkeypatch.setattr(native, "kill_tree", lambda proc: stopped.append(proc))

    class FakeProc:
        returncode = None
        def poll(self): return None

    def fake_start(name, command, **_kwargs):
        started.append(name)
        return name, FakeProc()
    monkeypatch.setattr(native, "start_service", fake_start)
    native.launch("start")
    assert started == ["prepare React", "React"]
    assert len(stopped) == 1
    stdout = capsys.readouterr().out
    assert "React http://127.0.0.1:5173 (started)" in stdout
    assert "Flask http://127.0.0.1:8000 (existing)" in stdout


def test_combined_launch_starts_missing_backend_when_react_already_running(monkeypatch):
    started = []
    monkeypatch.setattr(native, "config", lambda: {"KATS_LOCAL_ONLY": "1"})
    monkeypatch.setattr(native, "environment", lambda settings: {})
    monkeypatch.setattr(native, "select_backend_mode", lambda: "preview")
    monkeypatch.setattr(native, "existing_kats_service", lambda kind: kind == "frontend")
    monkeypatch.setattr(native, "frontend",
                        lambda **kwargs: (_ for _ in ()).throw(AssertionError("React already running")))
    monkeypatch.setattr(native, "backend", lambda: "python.exe")
    monkeypatch.setattr(native, "prepare_backend",
                        lambda *args: started.append("prepare Flask") or {})
    monkeypatch.setattr(native, "reachable", lambda url: True)
    checks = iter((False, True))
    monkeypatch.setattr(native, "stop_requested", lambda *_args: next(checks))
    monkeypatch.setattr(native, "kill_tree", lambda proc: None)
    class FakeProc:
        returncode = None
        def poll(self): return None
    monkeypatch.setattr(native, "start_service",
                        lambda name, command, **kwargs: (started.append(name) or (name, FakeProc())))
    native.launch("start")
    assert started == ["prepare Flask", "Flask"]



def test_fast_frontend_fails_immediately_without_vite_and_never_calls_install(monkeypatch, tmp_path):
    monkeypatch.setattr(native, "FRONT", tmp_path / "frontend")
    monkeypatch.setattr(native, "require", lambda command: "node.exe")
    monkeypatch.setattr(native.subprocess, "run",
                        lambda *_a, **_kw: SimpleNamespace(returncode=0, stdout="20"))
    monkeypatch.setattr(native, "invoke",
                        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("No npm ci during dev startup")))
    with pytest.raises(native.StartupError, match="Vite is not installed"):
        native.ready_frontend()
    vite = tmp_path / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    vite.parent.mkdir(parents=True)
    vite.write_text("/* vite executable */", encoding="utf-8")
    assert native.ready_frontend() == "node.exe"


def test_fast_backend_does_not_run_migrations_or_pip(monkeypatch, tmp_path):
    monkeypatch.setattr(native, "VENV", tmp_path / ".venv")
    monkeypatch.setattr(native, "STATE", tmp_path / ".local")
    python = tmp_path / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"stub python")
    monkeypatch.setattr(native.subprocess, "run",
                        lambda *_a, **_kw: SimpleNamespace(returncode=0))
    monkeypatch.setattr(native, "invoke",
                        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("No setup during dev startup")))
    with pytest.raises(native.StartupError, match="not initialized"):
        native.ready_backend("preview")
    database = tmp_path / ".local" / "kats-preview.sqlite3"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"existing local database")
    assert native.ready_backend("preview") == python


def test_fast_start_launches_frontend_without_waiting_for_flask(monkeypatch):
    started = []
    monkeypatch.setenv("KATS_FAST_START", "1")
    monkeypatch.setattr(native, "config", lambda: {"KATS_LOCAL_ONLY": "1"})
    monkeypatch.setattr(native, "environment", lambda *_a, **_kw: {})
    monkeypatch.setattr(native, "existing_kats_service", lambda kind: False)
    monkeypatch.setattr(native, "ready_frontend", lambda: started.append("Vite checked"))
    monkeypatch.setattr(native, "frontend",
                        lambda **_kw: (_ for _ in ()).throw(AssertionError("npm install forbidden")))
    monkeypatch.setattr(native, "backend",
                        lambda: (_ for _ in ()).throw(AssertionError("backend shouldn't run in UI task")))
    monkeypatch.setattr(native, "reachable",
                        lambda url: url == "http://127.0.0.1:5173/")
    monkeypatch.setattr(native, "verify_http_bridge",
                        lambda: (_ for _ in ()).throw(AssertionError("No Flask yet")))
    stops = iter([False, True])
    monkeypatch.setattr(native, "stop_requested", lambda *_a: next(stops))
    monkeypatch.setattr(native, "require", lambda *_a: "node.exe")
    monkeypatch.setattr(native, "kill_tree", lambda proc: None)

    class Proc:
        returncode = None
        def poll(self): return None
    monkeypatch.setattr(native, "start_service",
                        lambda name, *_a, **_kw: started.append(name) or (name, Proc()))
    native.launch("frontend")
    assert started == ["Vite checked", "React"]


def test_fast_backend_launches_without_initialization(monkeypatch):
    monkeypatch.setenv("KATS_SEED_DEMO", "1")
    started = []
    monkeypatch.setenv("KATS_FAST_START", "1")
    monkeypatch.setenv("KATS_DEV_BACKEND", "preview")
    monkeypatch.setattr(native, "config", lambda: {"KATS_LOCAL_ONLY": "1"})
    monkeypatch.setattr(native, "environment", lambda *_a, **_kw: {})
    monkeypatch.setattr(native, "existing_kats_service", lambda kind: False)
    monkeypatch.setattr(native, "select_backend_mode", lambda: "preview")
    monkeypatch.setattr(native, "ready_backend", lambda mode: started.append("Flask checked") or "python.exe")
    monkeypatch.setattr(native, "invoke", lambda args, **_kw: started.append("Preview seeded") if "seed_demo_preview.py" in str(args[-1]) else None)
    monkeypatch.setattr(native, "backend",
                        lambda: (_ for _ in ()).throw(AssertionError("No pip on quick start")))
    monkeypatch.setattr(native, "prepare_backend",
                        lambda *_a: (_ for _ in ()).throw(AssertionError("No SQL initialization on quick start")))
    monkeypatch.setattr(native, "reachable",
                        lambda url: url == "http://127.0.0.1:8000/readyz")
    monkeypatch.setattr(native, "verify_http_bridge",
                        lambda: (_ for _ in ()).throw(AssertionError("Vite not ready")))
    stops = iter([False, True])
    monkeypatch.setattr(native, "stop_requested", lambda *_a: next(stops))
    monkeypatch.setattr(native, "kill_tree", lambda proc: None)
    class Proc:
        returncode = None
        def poll(self): return None
    monkeypatch.setattr(native, "start_service",
                        lambda name, *_a, **_kw: started.append(name) or (name, Proc()))
    native.launch("backend-stack")
    assert started == ["Flask checked", "Preview seeded", "Flask"]


def test_dedicated_ports_match_shared_vite_config():
    import json
    expected = json.loads((ROOT / "ops" / "dev_ports.json").read_text(encoding="utf-8"))
    assert expected == {"frontend": 5173, "backend": 8000}
    assert native.FRONTEND_PORT == expected["frontend"]
    assert native.BACKEND_PORT == expected["backend"]
    assert native.FRONTEND_PORT != native.BACKEND_PORT
    vite = (ROOT / "frontend" / "vite.config.js").read_text(encoding="utf-8")
    assert "import ports from '../ops/dev_ports.json'" in vite
    assert "port: frontendPort" in vite and "strictPort: true" in vite
    assert "target: backend" in vite


def test_dedicated_port_contract_fails_closed_on_duplicate_or_invalid_ports(monkeypatch, tmp_path):
    directory = tmp_path / "ops"
    directory.mkdir()
    monkeypatch.setattr(native, "ROOT", tmp_path)
    for content in ('{"frontend":8000,"backend":8000}',
                    '{"frontend":"5173","backend":8000}',
                    '{"frontend":1023,"backend":8000}',
                    '{"frontend":5173,"backend":65536}'):
        (directory / "dev_ports.json").write_text(content, encoding="utf-8")
        with pytest.raises(native.StartupError, match="distinct ports"):
            native.load_service_ports()


def test_fast_backend_uses_lightweight_package_probe(monkeypatch, tmp_path):
    """Startup checks package presence, without eagerly importing Flask."""
    monkeypatch.setattr(native, "VENV", tmp_path / ".venv")
    monkeypatch.setattr(native, "STATE", tmp_path / ".local")
    python = tmp_path / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"stub python")
    calls = []
    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(native.subprocess, "run", fake_run)
    assert native.ready_backend("docker") == python
    assert len(calls) == 1
    assert "find_spec" in calls[0][0][2]
    assert "import flask," not in calls[0][0][2]
    assert calls[0][1]["timeout"] == 30


def test_fast_backend_probe_timeout_is_actionable(monkeypatch, tmp_path):
    monkeypatch.setattr(native, "VENV", tmp_path / ".venv")
    python = tmp_path / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"stub python")
    def timeout_run(args, **kwargs):
        raise native.subprocess.TimeoutExpired(args, kwargs["timeout"])
    monkeypatch.setattr(native.subprocess, "run", timeout_run)
    with pytest.raises(native.StartupError, match="exceeded 30 seconds"):
        native.ready_backend("docker")


def test_fast_backend_missing_packages_explains_setup(monkeypatch, tmp_path):
    monkeypatch.setattr(native, "VENV", tmp_path / ".venv")
    python = tmp_path / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"stub python")
    monkeypatch.setattr(native.subprocess, "run",
                        lambda *_a, **_kw: SimpleNamespace(returncode=1))
    with pytest.raises(native.StartupError, match="Native setup"):
        native.ready_backend("docker")
