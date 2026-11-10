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
    assert 'and reachable("http://127.0.0.1:5173/")' in source
    assert 'and reachable("http://127.0.0.1:8000/readyz")' in source
    assert 'verify_http_bridge()' in source
