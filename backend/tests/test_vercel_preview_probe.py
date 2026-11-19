"""Read-only Vercel client-review acceptance tests (no network)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))
from verify_vercel_preview import AcceptanceError, verify  # noqa: E402


ORIGIN = "https://kats-review-example.vercel.app"
ROOT_HTML = (b'<!doctype html><html lang="en"><div id="root"></div>'
             b'<script type="module" src="/assets/index-a1b2c3.js"></script></html>')


def fake_http(origin, path):
    assert origin == ORIGIN
    if path == "/readyz":
        return (200, {"content-type": "application/json",
                      "x-request-id": "test-only"}, b'{"status":"ready"}')
    if path in ("/", "/login"):
        return 200, {"content-type": "text/html"}, ROOT_HTML
    if path.startswith("/assets/"):
        return 200, {"content-type": "application/javascript"}, b"console.log('preview')"
    if path.startswith("/api/"):
        return 401, {"content-type": "application/json", "cache-control": "no-store",
                     "x-content-type-options": "nosniff"}, b'{"error":{"code":"UNAUTHORIZED"}}'
    if path == "/app-version.json":
        return 200, {"content-type": "application/json",
                     "cache-control": "no-store, max-age=0"}, b'{"version":"f00dbabe123456"}'
    if path == "/manifest.webmanifest":
        return 200, {"content-type": "application/manifest+json"}, b'{"display":"standalone"}'
    if path == "/sw.js":
        return 200, {"content-type": "application/javascript",
                     "cache-control": "no-cache, max-age=0"}, b"self.addEventListener('install', () => {})"
    raise AssertionError(f"Unknown test route {path}")


def test_read_only_vercel_acceptance_checks_api_db_pwa_and_version():
    result = verify(ORIGIN, fetch=fake_http)
    assert result["passed"] == len(result["checks"])
    names = {item["name"] for item in result["checks"]}
    assert {"backend_readiness", "database_readiness",
            "deployment_version_uncached", "installable_pwa",
            "service_worker", "worker_revalidates"}.issubset(names)


def test_vercel_acceptance_rejects_spa_html_as_release_metadata():
    def bad(origin, path):
        if path == "/app-version.json":
            return 200, {"content-type": "text/html"}, ROOT_HTML
        return fake_http(origin, path)

    with pytest.raises(AcceptanceError, match="deployment_version_not_html"):
        verify(ORIGIN, fetch=bad)


def test_vercel_acceptance_rejects_stale_release_cache():
    def bad(origin, path):
        status, headers, body = fake_http(origin, path)
        if path == "/app-version.json":
            return status, {**headers, "cache-control": "public, max-age=31536000"}, body
        return status, headers, body

    with pytest.raises(AcceptanceError, match="deployment_version_uncached"):
        verify(ORIGIN, fetch=bad)


def test_vercel_acceptance_rejects_missing_backend_and_protected_preview():
    def bad(origin, path):
        if path == "/readyz":
            return 200, {"content-type": "text/html"}, ROOT_HTML
        return fake_http(origin, path)

    with pytest.raises(AcceptanceError, match="backend_readiness"):
        verify(ORIGIN, fetch=bad)


def test_vercel_acceptance_rejects_http_nonpublic_and_foreign_redirect_urls():
    for invalid in ("http://kats-review-example.vercel.app", "https://127.0.0.1",
                    "https://kats-review-example.vercel.app/login",
                    "https://user:pass@kats-review-example.vercel.app"):
        with pytest.raises(AcceptanceError):
            verify(invalid, fetch=fake_http)
