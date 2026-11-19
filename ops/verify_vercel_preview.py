"""Read-only acceptance probe for a deployed KATS Vercel client review.

Does NOT log in, change demo data, seed, migrate, bypass deployment protection,
test real payments, or store private records. Share only successful public
evidence and obtain separate manual signoff for authenticated workflows.
"""
import argparse
import json
import re
import sys
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from verify_hostwares_live import AcceptanceError, http_get, validate_target, verify as verify_core


def verify(origin, fetch=http_get):
    """Verify full-stack readiness, immutable front end, PWA and update marker."""
    report = verify_core(origin, fetch=fetch)
    origin = validate_target(origin)
    checks = report["checks"]

    def check(name, passed, issue):
        if not passed:
            raise AcceptanceError(name + ": " + issue)
        checks.append({"name": name, "status": "PASS"})

    status, headers, body = fetch(origin, "/app-version.json")
    check("deployment_version_not_html", status == 200
          and "application/json" in headers.get("content-type", "")
          and b"<html" not in body.lower(),
          "Version endpoint must return JSON, not a Vite SPA fallback")
    try:
        metadata = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AcceptanceError("Version response is not JSON") from exc
    check("deployment_version_valid",
          isinstance(metadata, dict)
          and re.fullmatch(r"[A-Za-z0-9._-]{7,150}", str(metadata.get("version", ""))) is not None,
          "Missing or invalid built release ID")
    check("deployment_version_uncached",
          "no-store" in headers.get("cache-control", "").lower(),
          "Browser must always get fresh app-version metadata")

    status, headers, body = fetch(origin, "/manifest.webmanifest")
    check("pwa_manifest", status == 200 and "json" in headers.get("content-type", ""),
          "PWA manifest must exist with a JSON content type")
    try:
        manifest = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AcceptanceError("PWA manifest is not JSON") from exc
    check("installable_pwa", manifest.get("display") == "standalone",
          "Manifest must retain standalone installation")

    status, headers, body = fetch(origin, "/sw.js")
    check("service_worker", status == 200
          and b"addEventListener" in body
          and ("javascript" in headers.get("content-type", "")
               or "ecmascript" in headers.get("content-type", "")),
          "Service worker must be served as executable JS")
    check("worker_revalidates",
          "no-cache" in headers.get("cache-control", "").lower()
          or "no-store" in headers.get("cache-control", "").lower(),
          "Service worker cannot be indefinitely cached")

    report["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["passed"] = len(checks)
    report["scope"] = "Vercel read-only React + Flask/PostgreSQL + anonymous RBAC + PWA"
    report["not_proven"].extend([
        "Vercel account commercial-plan eligibility",
        "real always-on Redis/Celery worker and scheduled tasks",
        "reviewer sign-in and tenant/owner end-to-end operations",
        "seeded fictional database contents and migrations",
        "email invitations and MFA enrollment",
        "deployment protection behavior for invited reviewers",
    ])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True,
                        help="Actual HTTPS review origin, without path, credentials or query")
    parser.add_argument("--evidence", help="Private JSON output path (no credentials)")
    args = parser.parse_args(argv)
    try:
        result = verify(args.url)
    except (AcceptanceError, urllib.error.URLError, TimeoutError, OSError) as exc:
        print("VERCEL REVIEW VERIFICATION FAILED: " + str(exc), file=sys.stderr)
        return 1
    if args.evidence:
        file = Path(args.evidence)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
