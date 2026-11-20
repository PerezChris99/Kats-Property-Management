# KATS client review on Vercel — pre-Hostwares sandbox

**Scope:** one private Kats Properties business. This is client user-acceptance testing,
**not** SaaS launch, not a production release, and never a reason to import real
tenant, payment, identity, bank or financial data. Hostwares remains the later
production target. A GitHub build passing is not proof a Vercel URL is working.

## 1. Account and release boundary

The connected Vercel team was on the **Hobby** plan when prepared. Vercel's
Hobby terms restrict use to personal/non-commercial projects, so **upgrade to
Pro or use a suitably authorized commercial team before exposing this business
application to the client**. No live project or URL is created merely by these
source changes.

In Vercel, connect the private GitHub repository
`PerezChris99/Kats-Property-Management` under the approved account:

- Project name: e.g. `kats-properties-client-review` (choose the real project
  name once; do not claim that a specific URL exists until Vercel assigns it).
- **Root Directory: repo root** (`.`), NOT `frontend`; the repo-root
  `vercel.json` declares `services.web` at `frontend/` and `services.api`
  at `backend/` with `entrypoint: wsgi:app`.
- Git production branch: `main`. Treat Vercel's `production` *target* as
  a **fictional-data review site** in business terms, not the actual business
  launch. `perez` PRs can produce protected preview builds before merging.
- Retain Vercel's deployment protection for private previews and configure
  approved reviewers using Vercel project controls. Verify reviewer access,
  don't paste bypass cookies or tokens into files or chat. Hostwares rollout
  must use its own release approval.
- Avoid installing a second standalone frontend-only Vercel project: it would
  show a website while silently losing Flask, auth, rent and DB functionality.

Root rewrites route `/api/*`, `/healthz`, `/readyz` to Flask and all other
paths to Vite React. Changes to `main` build the next Vercel release when
Git deployment is enabled; the existing browser/PWA version checker then
detects the new *deployed* build.

## 2. External services required for real-time functional testing

**PostgreSQL**: prepare a NEW, dedicated managed PostgreSQL database, such
as isolated Neon `katsproperty`, with independent backups and TLS
`sslmode=verify-full`. Do not use the live Hostwares database, existing
business records, or the developer's local DB. The backend **must** use a
restricted runtime DB role (not owner/superuser/BYPASSRLS). Run migrations
separately with a migration role before enabling web traffic. For elastic
serverless connections, use the provider's connection pooler and keep
`DB_POOL_SIZE=1`, `DB_MAX_OVERFLOW=0`; set provider connection limits.

**Redis is NOT required for client review.** Use `RATELIMIT_STORAGE_URI=katsdb://`
with migration `0036_postgres_rate_limits`. This registers a shared,
PostgreSQL-backed, atomic fixed-window limiter across Vercel instances.
It fails closed if PostgreSQL/table access fails and hashes keys so no raw
client-IP identifier is stored. Never substitute `memory://` on a public,
multi-instance site. Periodically prune expired counters with an authorized
database maintenance job.

**Background work**: set `KATS_TASK_MODE=inline` for the isolated demo.
Request-triggered operations dispatch synchronously without a Redis broker.
**Timed tasks are NOT automatic** on Vercel Functions: monthly rent generation,
lease reminders, retention pruning and preventive maintenance still need a
separate explicitly scheduled execution using protected CLI commands. Unless
such a scheduler is configured and verified, exclude these scheduled flows
from client acceptance; never claim an always-on Celery worker exists.
Payment/fiscal integrations must stay disabled in inline mode.

**Email & files**: for invitation, recovery and MFA user journeys, configure a
verified **test** SMTP sender. A private document store plus malware scanning
is required to exercise real attachments. If not provisioned, exclude those
operations from acceptance. Disable **MTN MoMo, Airtel Money and EFRIS** and
do not use real funds or tax submissions.

## 3. Database lifecycle (operator controlled)

Use a one-off protected administration environment, not the Vercel HTTP
request handler, to perform migrations and seed demo records. Keep *migration*
credentials separate from the restricted runtime role.

Run in the repository, with `backend` dependencies installed and all real
values supplied by a secrets manager. For a fresh dedicated Neon
`katsproperty` database, prefer the guarded all-in-one command; it migrates
the complete Alembic chain, seeds permissions, writes only fictional records
and verifies schema head and 31 accounts:

```bash
# Protected operator session only: NOT in a public function, deploy hook, or CI.
# APP_ENV=staging, KATS_NEON_SETUP=1, KATS_PUBLIC_DEMO_SEED=1,
# KATS_TASK_MODE=inline, KATS_PUBLIC_DEMO_PASSWORD=<strong-fictional-only>
python ops/setup_neon_demo.py
```

For a migration-only installation (no demo seed), use the explicit steps below.
Use separate restricted `kats_runtime` credentials for the Vercel app and
database-owner credentials only for the one-time operator migration:

```bash
# Protected admin session: APP_ENV=staging, dedicated migration DB role.
cd backend
python -m flask --app wsgi db upgrade
python -m flask --app wsgi seed-permissions
cd ..
```

The repository also includes `ops/seed_neon_demo.py` for an *optional one-time*
31-account entirely fictional dataset. **Only** use its guarded
`APP_ENV=staging`, `KATS_PUBLIC_DEMO_SEED=1` mode against a dedicated,
already migrated `katsproperty` Neon database after inspecting the seed
guard and verifying that the database has no real records. Supply
`KATS_PUBLIC_DEMO_PASSWORD` as a unique 16+ character fictional-only value
via the secrets manager and run:

```bash
python ops/seed_neon_demo.py
```

This demo password is **not** an administrator/business secret. If the public
demo selector is explicitly enabled, the same value goes into
`VITE_KATS_DEMO_PASSWORD`, which is **embedded in browser JavaScript**.
That setting is only acceptable for fictitious accounts in a protected demo,
never real users. By default keep `VITE_KATS_PUBLIC_DEMO=false` and invite
specifically approved testers instead.

After migration, verify the restricted runtime role, current Alembic revision,
RLS policies and the shared PostgreSQL limiter with the existing
`python -m app.release_preflight` command from inside `backend/`.
Do not declare the full system ready based solely on the migrations.

## 4. Environment variables

Copy names (not literal placeholder values) from `ops/vercel.env.sample`
into Vercel **encrypted Environment Variables** for the designated review
deployment environment, including:

| Group | Required settings |
| --- | --- |
| Runtime | `APP_ENV=production`, `COOKIE_SECURE=true`, `KATS_PREVIEW_MODE=0`, `PUBLIC_REGISTRATION_ENABLED=false` |
| Host restriction | `CORS_ORIGINS` and `TRUSTED_HOSTS` for the **approved exact HTTPS review origin**; `PUBLIC_APP_URL` for links |
| DB | `DATABASE_URL` with restricted pooled Postgres role, `sslmode=verify-full`, and small connection pool |
| Shared limits and tasks | `RATELIMIT_STORAGE_URI=katsdb://`, `KATS_TASK_MODE=inline`; PostgreSQL migration 0036 |
| Secrets | Distinct high-entropy `SECRET_KEY`, `JWT_SECRET_KEY`, plus valid `MFA_ENCRYPTION_KEY` |
| External payments | All `MTN_MOMO_ENABLED`, `AIRTEL_MONEY_ENABLED`, `EFRIS_ENABLED` **false** |
| Frontend | `VITE_KATS_PUBLIC_DEMO=false` unless using only the protected fictional demo |

Vercel automatically injects `VERCEL=1`, `VERCEL_ENV` and `VERCEL_URL`.
Do **not** set those yourself. KATS validates the exact
`*.vercel.app` deployment hostname and adds its HTTPS origin to the existing
explicit allowlist. This permits ephemeral PR URLs without wildcard CORS or
opening Hostwares to arbitrary origin headers. A fake hostname, port, path,
protocol or unrelated host is rejected.

**Important:** A deployment may have its own immutable hostname different
from the project's stable review alias. Only the current Vercel-assigned host
is admitted dynamically. For invitations and links use a stable, approved
review hostname. All API traffic and cookies remain same-origin.

## 5. End-to-end acceptance before handing the link to the client

Wait for Vercel to report **READY** and confirm deployment protection access.
Then verify the actual HTTPS URL:

```bash
python ops/verify_vercel_preview.py \
  --url https://YOUR-ACTUAL-REVIEW-HOST.vercel.app \
  --evidence .local/vercel-client-review-evidence.json
```

The verifier is read-only. It proves real Flask + PostgreSQL `/readyz`
response (not SPA HTML), request ID, built React asset, deep `/login`
route, anonymous tenant/owner API isolation, uncached `app-version.json`,
PWA manifest, 192px/512px PNG icons and a revalidating service worker. It exits nonzero on any
mismatch. If Vercel deployment protection blocks anonymous verification,
use an authorized testing method within the owner's environment; **do not
disable protection merely to make automated checks pass**.

Run authenticated manual review separately: approved staff and tenant logins,
MFA, each role's dashboard, rent/invoices/verified vs recorded payments,
maintenance mutations, landlord/tenant isolation, session refresh, browser
and installed PWA, reconnection and **Get new update** after a subsequent
deployment. Exercise mail, attachments and scheduled jobs only when their
external services are actually operating. Record defects and signoff without
real person/tenant information.

## 6. Transition to Hostwares

Use `compose.hostwares.yml`, `docs/HOSTWARES_DEPLOYMENT.md` and the
normal Hostwares production preflight. Hostwares gets a **separate**
database, keys, mail configuration, backups and approvals. Hostwares may
retain separately managed Redis/Celery if that deployment later needs it; the
Vercel client review does not.
Never copy a fictional Vercel snapshot into the real Kats Properties ledger.
After Hostwares cutover, retire/restrict the client-review stack, revoke
reviewer accounts and keep an auditable acceptance record. The Vercel site
is a convenience for testing, not evidence of completed live finance,
security, backup or compliance signoff.

## 7. Invitations, recovery and PWA acceptance

The backend already has approved `POST /api/v1/admin/invitations`, resend,
`POST /api/v1/auth/recover` and one-use `POST /api/v1/auth/complete-token`
flows. Owner UI exposes **Invitations** and login exposes **Forgot password**;
links contain bearer tokens in the URL **fragment** and never return them in
admin API responses. `GET /api/v1/admin/invitations/status` now reports
configured/unconfigured SMTP **only to authorized owners**, without credentials.

Set a verified test `SMTP_HOST`, `SMTP_PORT` (465 or 587),
`SMTP_USERNAME`, `SMTP_PASSWORD` and `MAIL_FROM` in encrypted Vercel env
settings; send an invite to an approved *fictional test mailbox*, activate,
reset, resend and prove old tokens/session credentials are invalidated.
An HTTP test proves workflow behavior, **not** that SMTP delivered a message.

The PWA has `manifest.webmanifest` with standalone mode, 192x192 PNG and
512x512 padded maskable PNG icons, production-only service-worker
registration, separate offline fallback, **no private API caching**, and
release-update discovery. Test installation from HTTPS using a real current
Android Chrome / desktop Chromium browser and validate offline screen,
login when reconnected and user-initiated version upgrade. Source-level PWA
checks are not proof of actual installation or push notification support.
