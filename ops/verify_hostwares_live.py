"""Read-only HTTPS production acceptance probe for a Hostwares KATS deployment.

No credentials, writes, user data, external redirects, or production mutations.
Use only after the owner has deployed to a Hostwares HTTPS hostname.
"""
import argparse
import ipaddress
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

MAX_BODY = 256 * 1024
PRIVATE_PATHS = (
    "/api/v1/auth/me",
    "/api/v1/analytics/landlord/portfolio",
    "/api/v1/analytics/tenant/payment-history",
    "/api/v1/operations/assets",
)


class AcceptanceError(Exception):
    pass


def validate_target(value):
    parsed = urlsplit(value)
    hostname = parsed.hostname or ""
    if (parsed.scheme != "https" or not hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")
            or parsed.port not in (None, 443)):
        raise AcceptanceError("Use a bare public HTTPS deployment origin, without credentials or paths.")
    if hostname in ("localhost", "127.0.0.1", "::1") or hostname.endswith((".local", ".internal")):
        raise AcceptanceError("The live verifier requires a public deployment hostname.")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise AcceptanceError("Use the Hostwares public DNS name, not an IP address.")
    return parsed.scheme + "://" + hostname + (":443" if parsed.port == 443 else "")


def http_get(origin, path, timeout=12):
    request = urllib.request.Request(
        origin + path, method="GET",
        headers={"User-Agent": "KATS-Hostwares-ReadOnly-Acceptance/1.0", "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            headers = dict(response.headers.items())
            data = response.read(MAX_BODY + 1)
            final_url = response.geturl()
    except urllib.error.HTTPError as response:
        status = response.code
        headers = dict(response.headers.items())
        data = response.read(MAX_BODY + 1)
        final_url = response.geturl()
    if len(data) > MAX_BODY:
        raise AcceptanceError("Oversized response for " + path)
    if (urlsplit(final_url).scheme, urlsplit(final_url).netloc) != (
            urlsplit(origin).scheme, urlsplit(origin).netloc):
        raise AcceptanceError("Cross-origin redirect detected at " + path)
    return status, {k.lower(): v for k, v in headers.items()}, data


def verify(origin, fetch=http_get):
    """Return a public-only evidence record, or fail closed on mismatch."""
    origin = validate_target(origin)
    checks = []

    def assert_check(name, predicate, description):
        if not predicate:
            raise AcceptanceError(name + ": " + description)
        checks.append({"name": name, "status": "PASS"})

    status, headers, body = fetch(origin, "/readyz")
    assert_check("backend_readiness", status == 200 and
                 headers.get("content-type", "").startswith("application/json"),
                 "Flask readiness must return JSON 200")
    try:
        readiness = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AcceptanceError("Flask readiness returned malformed JSON") from exc
    assert_check("database_readiness", readiness.get("status") == "ready",
                 "Flask must confirm its database SELECT 1")
    assert_check("api_request_id", bool(headers.get("x-request-id")),
                 "Flask must return an X-Request-ID")

    status, headers, body = fetch(origin, "/")
    assert_check("frontend_html", status == 200 and "text/html" in headers.get("content-type", "") and
                 b'id="root"' in body, "Serve the built React index.html from the same origin")
    text = body.decode("utf-8", errors="replace")
    asset = re.search(r'<script[^>]*src=["\'](/assets/[^"\']+\.js)["\']', text)
    assert_check("production_js_bundle", asset is not None,
                 "Production index must reference a hashed Vite JS bundle, not a dev server")
    if asset:
        status, headers, _body = fetch(origin, asset.group(1))
        assert_check("javascript_bundle", status == 200 and
                     ("javascript" in headers.get("content-type", "") or
                      "ecmascript" in headers.get("content-type", "")),
                     "Built React JS bundle missing or served as HTML")

    status, headers, body = fetch(origin, "/login")
    assert_check("spa_login_fallback", status == 200 and b'id="root"' in body,
                 "Deep-linked login must deliver the React shell")

    for path in PRIVATE_PATHS:
        status, headers, _body = fetch(origin, path)
        assert_check("unauthorized_" + path.removeprefix("/api/v1/").replace("/", "_"),
                     status in (401, 422), path + " exposed private records to an anonymous visitor")
        assert_check("no_cache_" + path.removeprefix("/api/v1/").replace("/", "_"),
                     "no-store" in headers.get("cache-control", "").lower(),
                     path + " must never cache private data")
        assert_check("nosniff_" + path.removeprefix("/api/v1/").replace("/", "_"),
                     headers.get("x-content-type-options", "").lower() == "nosniff",
                     path + " missing nosniff protection")

    return {
        "deployment_origin": origin, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks, "passed": len(checks),
        "scope": "read-only public HTTPS, Flask SQL readiness, frontend bundle and anonymous authorization",
        "not_proven": [
            "signed-in owner/tenant workflows",
            "mobile physical-device behavior",
            "payment settlement and webhook roundtrip",
            "production backups/restoration",
            "full penetration testing and legal compliance",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Live public Hostwares HTTPS app origin")
    parser.add_argument("--evidence", help="Optional JSON evidence path (no secrets)")
    args = parser.parse_args(argv)
    try:
        report = verify(args.url)
    except (AcceptanceError, urllib.error.URLError, TimeoutError, OSError) as exc:
        print("LIVE VERIFICATION FAILED: " + str(exc), file=sys.stderr)
        return 1
    if args.evidence:
        path = Path(args.evidence)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
