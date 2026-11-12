"""Read-only Hostwares HTTPS acceptance probe must reject leaks and false-ready pages."""
import importlib.util
from pathlib import Path
import pytest

SOURCE = Path(__file__).resolve().parents[2] / "ops" / "verify_hostwares_live.py"
spec = importlib.util.spec_from_file_location("hostwares_live_probe", SOURCE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

ORIGIN = "https://kats.example.com"
PRIVATE = {
    "content-type": "application/json", "cache-control": "no-store",
    "x-content-type-options": "nosniff",
}

def fixture_fetch(_origin, path):
    if path == "/readyz":
        return 200, {"content-type": "application/json",
                     "x-request-id": "test-request-id"}, b'{"status":"ready"}'
    if path in ("/", "/login"):
        return 200, {"content-type": "text/html; charset=utf-8"}, (
            b'<html><div id="root"></div><script type="module" '
            b'src="/assets/index-123456.js"></script></html>')
    if path == "/assets/index-123456.js":
        return 200, {"content-type": "text/javascript"}, b'console.log("test");'
    assert path in probe.PRIVATE_PATHS
    return 401, PRIVATE, b'{"error":{"code":"UNAUTHORIZED"}}'


def test_hostwares_probe_success_requires_secure_real_stack():
    report = probe.verify(ORIGIN, fixture_fetch)
    assert report["passed"] == len(report["checks"])
    assert len(report["checks"]) >= 15
    assert all(item["status"] == "PASS" for item in report["checks"])
    assert "mobile physical-device behavior" in report["not_proven"]


@pytest.mark.parametrize("target", [
    "http://kats.example.com", "https://localhost", "https://127.0.0.1",
    "https://kats.example.com/api/health", "https://user:password@kats.example.com",
    "https://kats.example.com?token=secret", "https://10.0.0.4"
])
def test_reject_invalid_or_nonproduction_target(target):
    with pytest.raises(probe.AcceptanceError):
        probe.validate_target(target)


def test_probe_rejects_public_finance_exposure():
    def leaky_fetch(origin, path):
        status, headers, body = fixture_fetch(origin, path)
        if path.endswith("/analytics/landlord/portfolio"):
            return 200, headers, b'{"points":[{"name":"Private"}]}'
        return status, headers, body
    with pytest.raises(probe.AcceptanceError, match="exposed private records"):
        probe.verify(ORIGIN, leaky_fetch)


def test_probe_rejects_fake_html_or_missing_request_id():
    def fake_ready(origin, path):
        status, headers, body = fixture_fetch(origin, path)
        if path == "/readyz":
            return 200, {"content-type": "text/html"}, b'<html>healthy</html>'
        return status, headers, body
    with pytest.raises(probe.AcceptanceError, match="backend_readiness"):
        probe.verify(ORIGIN, fake_ready)


def test_probe_rejects_missing_frontend_asset():
    def missing_bundle(origin, path):
        status, headers, body = fixture_fetch(origin, path)
        if path.startswith("/assets/"):
            return 404, {"content-type": "text/html"}, b'not found'
        return status, headers, body
    with pytest.raises(probe.AcceptanceError, match="javascript_bundle"):
        probe.verify(ORIGIN, missing_bundle)
