# KATS Vercel + Neon deployment

**Status (11 November 2026): source prepared; NOT live.** An authenticated Vercel project-creation request for the exact name `katsproperty` returned HTTP 403 forbidden, including the alternate project-creation API. No Vercel deployment or default-domain reservation succeeded. The Neon project `little-mountain-04838983` (`katsproperty-demo`), PostgreSQL 17, AWS US East, has been provisioned but is not migrated or seeded. Do not report that a public login works.

## Application architecture

This repository is **Flask + React/Vite**, not NextAuth or Next.js. The Vercel Services manifest at `/vercel.json` describes a `frontend/` Vite web service and `backend/` Flask API service via `wsgi:app`. It routes `/api/*`, `/healthz`, and `/readyz` to Flask and everything else to React. The frontend service retains SPA deep links.

The runtime presently requires **Redis for shared rate limits** and **a Celery worker + scheduler for recurring jobs**. Vercel hosting and Neon alone do not supply those services. Do not set Flask-Limiter to memory in production, mark a queue integration configured without testing it, or claim payments/notifications are live. Managed Redis and a compatible worker/scheduler or verified Vercel Queues/Celery integration must be approved before release. External MTN/Airtel/EFRIS and file-storage/scan providers remain disabled unless independently configured and accepted.

## Public demonstration safety model

The optional Vite build settings `VITE_KATS_PUBLIC_DEMO=true` and `VITE_KATS_DEMO_PASSWORD` (minimum 12 chars) render **Demo Accounts — for testing only** beside the standard sign-in form. The panel visibly displays the password and one-click **form-fill** shortcuts for `landlord@demo.kats.invalid` and `tenant01@demo.kats.invalid` through `tenant30@demo.kats.invalid`. Authentication still requires the real Flask `/api/v1/auth/login` path; no bypass is introduced.

**These credentials are PUBLIC by design. Never give publicly disclosed accounts real customer data, live financial-provider access, keys, unrestricted storage access, or meaningful business privileges.** The synthetic owner can edit synthetic data in the dedicated demonstration database; it is not a production administrator for any real customer. Enforce provider-disabled flags; no live transactions.

The seed script `ops/seed_neon_demo.py` is separately invoked and **never runs during ordinary web application boot**. It insists on a dedicated Neon database named `katsproperty`, `APP_ENV=staging`, `KATS_PUBLIC_DEMO_SEED=1`, a 16+ character demo password, and disabled payment/fiscal flags. It refuses a nonempty database containing real users or a partial demo dataset, uses Argon2id for stored password hashes, and reuses the 31-account synthetic portfolio dataset. The local SQLite preview seed retains its original safeguards.

## Required secrets and connection roles

Set these securely in the Vercel production project **after permissions are resolved**: `APP_ENV=production`, `DATABASE_URL` (Neon **pooled** URL for a restricted, non-owner, non-BYPASSRLS runtime role; `sslmode=verify-full`), `SECRET_KEY`, `JWT_SECRET_KEY` (independent 32+ character random secrets), `REDIS_URL` and `RATELIMIT_STORAGE_URI` (managed TLS Redis), `COOKIE_SECURE=true`, `CORS_ORIGINS=https://katsproperty.vercel.app`, `TRUSTED_HOSTS=katsproperty.vercel.app`, and approved Celery broker/result settings. For demo presentation, also set `VITE_KATS_PUBLIC_DEMO=true` and `VITE_KATS_DEMO_PASSWORD` to the public synthetic account password used during seeding. Do not expose the migration-owner connection string in Vercel runtime environments or Git.

The **direct, unpooled connection** and a separate migration/owner role belong only in an isolated migration runner. Migrations are never triggered by each serverless cold start. Production must pass `security-preflight` and `release_preflight` using restricted runtime credentials.

## Migration/seed procedure (NOT yet executed)

1. Resolve Vercel account access to create a project (the connector currently gets 403) and confirm entitlement to Services and the proposed worker execution model. Reserve `katsproperty` and confirm `katsproperty.vercel.app`; project creation does not guarantee global subdomain availability.
2. Provision a dedicated **non-BYPASSRLS** runtime role and direct migration owner on Neon. Verify actual CA and TLS settings and available connection limits; bind Vercel to the pooled runtime connection.
3. Run `cd backend && python -m flask --app wsgi db upgrade` in an approved isolated migration environment with direct migration credentials. Verify revision `0027_maintenance_idempotency`, composite indexes and all seven FORCE RLS policies.
4. Run `python -m flask --app wsgi seed-permissions` with the migration role, then `KATS_PUBLIC_DEMO_SEED=1 APP_ENV=staging KATS_PUBLIC_DEMO_PASSWORD=<synthetic-demo-secret> python ../ops/seed_neon_demo.py` with the same direct isolated Neon database URL. The password is supplied from a secret manager, not committed to Git. Note that `VITE_KATS_DEMO_PASSWORD` is deliberately displayed publicly and must equal the seeded demo password.
5. Verify counts and FKs directly on Neon: 31 users (1 OWNER, 30 TENANT), 30 tenant profiles, 30 active leases, 3 properties, 33 rooms (30 occupied), 60 invoices, and test payments/maintenance. Check tenant A cannot view tenant B's invoices, and verify actual password authentication with all 31 test accounts.
6. With one reviewed commit and all existing CI checks passing, link the Git repository to the exact Vercel project, configure runtime environment variables, perform **one** production deployment, and check `/readyz`, `/api/v1/auth/me`, responsive UI, demo credentials beside sign-in, all sample login sessions, negative RBAC probes, rate limits, error logs, and DNS.
7. Do not mark production accepted without external Redis/worker configuration, data restoration, backups/PITR, incident response, independent security review, provider certification, and an observed load test.

## Evidence and blockers

- **Neon:** project exists; schema and dataset remain unverified/unseeded.
- **Vercel:** connected user/team lacks project-creation permission (403). There is no verified `katsproperty.vercel.app` deployment.
- **Source:** preparatory Vercel Services manifest, SPA rewrites, explicit sample login pane, guarded synthetic seeder and regression tests are in GitHub.
- **No credentials or downloaded `.env` files are committed.** Vercel's connected account must be granted project creation permission or a project named `katsproperty` must be created under an account where this connector has Editor access, then execution can resume with real credentials and services.
