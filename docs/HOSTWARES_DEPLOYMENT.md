# KATS Hostwares staging and production acceptance

**Not yet live-deployed or physically device-verified.** This repository now includes a Hostwares-targeted Compose variant and an actual external HTTPS verifier; deployment readiness is not evidence that a Hostwares project, database, domain or TLS certificate has been provisioned.

## Infrastructure gate

Provision separate staging and production HostWares VPS environments with restricted SSH keys, patched Ubuntu LTS, a firewall with only necessary ports, unique long environment secrets, and dedicated PostgreSQL credentials. Start with 2 vCPU, 4 GB RAM and 80 GB SSD only as a proposed baseline; size using load tests.

Terminate HTTPS at Nginx or Caddy with managed certificate renewal. Require secure session cookies, HTTPS CORS allowlist, HSTS, CSP and signed object-storage file delivery. Do not expose the API or PostgreSQL directly.

## Data and recovery

Set AGE_RECIPIENT to an independently controlled public encryption key and run ops/backup-postgres.sh. Store backups off the VPS with retention, integrity checks and access controls. Weekly, execute ops/restore-staging.sh using AGE_IDENTITY on an isolated staging instance. No production restore command is provided intentionally. Run data count, invoice balance and ledger integrity checks after restoring.

## Release order

1. Pull only a reviewed main commit and keep an immutable image/tag reference.
2. Snapshot and back up current database before a migration.
3. Run backend tests, frontend production build and schema migrations on staging.
4. Check security headers, endpoints, role permissions, privacy and failure states.
5. Run ops/smoke-test.sh against the staging URL.
6. Exercise latency/3G, retry and load tests and verify incidents and alerts.
7. Obtain landlord signoff and tax/payment provider acceptance before production promotion.
8. Confirm production offsite backup, restore evidence and rollback option.
9. Promote and observe the first rent cycle with dedicated on-call support.

## Rollback and incident safety

If a deployment fails, stop writes where needed, preserve a forensic and encrypted backup, and revert to the last compatible image. Schema incompatibility requires a controlled recovery decision. Never delete or rewrite posted monetary records. Coordinate external reconciliation with banks, MTN, Airtel or URA according to the provider and taxpayer rules.

## Monitoring

Configure real uptime, logs, error and resource alerts for API, PostgreSQL, Redis, Celery queues, disk capacity, TLS expiry, failed logins, payment reconciliation and EFRIS submission. All must be tested on real infrastructure. Documentation is not proof that any monitor or alert exists.

## Account and permission activation

Before onboarding any users on staging, configure `PUBLIC_APP_URL=https://<approved-domain>`, set all `SMTP_*` values and `MAIL_FROM` for a verified transactional SMTP sender, and keep `PUBLIC_REGISTRATION_ENABLED=false`. Production rejects self-registration and owner-provided shared initial passwords. Verify mail domain DNS (SPF, DKIM, DMARC), onboarding link expiry, resend, password recovery, account suspension and logout invalidation.

After every application migration, run `flask --app wsgi seed-permissions`; permission grants are persisted and the server refuses unknown protected routes in production until seeded. Preserve current grants and audit changes with an authorized super administrator.

## Financial acceptance gate

Check the staff expense reviewer queue before relying on margin reports: legacy migrated expense rows are `REVIEW_REQUIRED` until independently rechecked. Calendar-day rent proration must be legally and contractually approved before a finance officer issues any such invoice. Annual trends derive collections from verified settlement timestamps, not payment creation time; historical payments without trusted settlement timestamps require separate reconciliation.


## Hostwares managed deployment (private single-owner system)

Hostwares documentation supports GitHub/private repos, Docker/Compose, custom ports,
managed PostgreSQL, HTTPS, backups and image rollback:
https://hostwares.com/docs/deployments and https://hostwares.com/docs/databases .

Use the `main` branch and the repo-root `compose.hostwares.yml` as a
**multi-service** deployment. It builds a React+nginx `web`, Flask `api`,
Celery `worker` and `beat`. Hostwares terminates TLS and routes its public
site to the `web` service on the configured `HOSTWARES_PORT` (default
8080). The app's `/api/` and `/readyz` are reverse proxied to the private
`api` service. Do not expose Flask, PostgreSQL or Redis publicly.

Provision private PostgreSQL with a restricted user, TLS CA and
`sslmode=verify-full`, plus private Redis. Set **all required** production
environment secrets in Hostwares' encrypted site settings (see
`ops/production.env.sample`); do not commit or share them. Use an explicitly
approved HTTPS `PUBLIC_APP_URL`, `CORS_ORIGINS`, and `TRUSTED_HOSTS`.
Keep external payment/fiscal gateways disabled until formally approved.

Before enabling public traffic run, in the protected production API runtime:
`python -m flask --app wsgi db upgrade`,
`python -m flask --app wsgi seed-permissions`, and
`python -m app.release_preflight`. Create the OWNER using the existing
protected owner setup and enroll MFA for all active privileged accounts.
A live promotion is blocked until these checks and managed backup restore
evidence are recorded.

### Local configuration contract check

```bash
docker compose --env-file ops/production.env.sample \
  -f compose.hostwares.yml config --quiet
```

### Public HTTPS read-only verification

After Hostwares actually assigns a hostname and completes deployment:

```bash
python ops/verify_hostwares_live.py \
  --url https://YOUR-REAL-HOSTWARES-HOSTNAME \
  --evidence .local/hostwares-live-acceptance.json
```

The probe verifies a TLS-validated HTTPS origin, Flask/PostgreSQL readiness,
request IDs, the built React HTML and JS assets, deep-linked `/login`, and
that private finance/asset API routes deny anonymous access and cannot be
cached. It uses **GET only**, with no credentials or writes. Tests deliberately
reject a fake HTML health response, a missing bundle or an exposed API.

If no public deployment URL is available, this gate is **NOT TESTED**, not
passed. Deployment status `RUNNING` alone does not prove security or that
the right app version is live.

### Physical-device release gate

Chromium touch emulation in `ops/test_browser_e2e.py` exercises viewport,
DPR, tap, Recharts resizing and console/page-error safety for common Android,
iPhone-sized and tablet-sized screens. It **does not run iOS Safari,
Samsung Internet, or any real device**.

An actual operator must record pass/fail evidence for: (1) a low-end Android
phone with Chrome over throttled mobile data, (2) a second Android with Samsung
Internet, (3) a physical iPhone Safari, and (4) an iPad Safari. On each,
sign in as a disposable authorized role, test MFA, charts/tooltip touch,
readability, tenant permission isolation, page refresh and navigation,
offline/reconnect, and real form/receipt/maintenance flows. Repeat after fixes
and preserve a private device/OS/browser/date/result issue record. Never use
screenshots exposing real tenant data.

**Required live evidence still outstanding:** Hostwares project/deployment ID,
verified public origin and certificate, actual API/database smoke results,
MFA sign-in and recovery, offsite restore demonstration, worker/Redis task
recovery, real physical-device signoff and any real payment/fiscal provider
transactions. Do not mark them complete based solely on GitHub Actions.
