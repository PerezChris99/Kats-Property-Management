# KATS Property Management

**A private, mobile-first property operations platform for Kats Properties, Uganda.**

Manage a single business's properties, tenants, leases, rent, maintenance and financial records in one role-controlled workspace. Designed for daily operations across the owner's portfolio—not a SaaS service for unrelated landlords. All monetary values are recorded in integer **Uganda shillings (UGX)**.

> **Release status:** The source has automated CI coverage, including PostgreSQL, browser and Windows launcher checks. **Production deployment, bank/payment integrations, data migration, live-device testing and client acceptance are not yet signed off.** CI success does not certify production readiness or authorize real-money or fiscal operations.

## Product boundary

KATS is **one private property-management system belonging to Kats Properties**. Its owner, authorized staff, caretakers and tenants use it to operate the business's buildings and rental units. It is **not software-as-a-service**, not a multi-organization landlord marketplace, and not a subscription product marketed to other property businesses.

- Public pages explain Kats Properties' own property operations; they must not solicit independent landlords, advertise SaaS plans, trials or external customer onboarding.
- The public **Request access** form is an administrator-reviewed request for people already associated with Kats Properties. It does not self-register a new business, property company or independently provision an account.
- Multiple properties, rooms, leases, user roles and access boundaries are internal business records. Preserve privacy and permission controls; do not interpret them as authorization to build SaaS tenant onboarding.
- Supporting property photos on public pages are **illustrative only**: no claim that photographed buildings belong to or are managed by Kats Properties. Retain all external photo licences and credits in the existing application's **Image attributions** page (`/image-attributions`); do not add intrusive photo-credit banners to the navigation.

## What it does

| Workspace | Core functionality |
| --- | --- |
| **Owner & management** | Properties, buildings, floors, rooms, occupancy, staff roles, invitations and oversight |
| **Tenancies** | Tenant records, leases, renewals, inspections, deposits, notices and disputes |
| **Rent & accounting** | Invoices, collections, arrears, expenses, immutable general ledger, controlled corrections and reviewed bank-statement reconciliation |
| **Operations** | Maintenance requests, work orders, caretaker assignments, preventive plans, equipment and utility readings |
| **Tenant portal** | Scoped lease, invoice, payment, maintenance, document and notification views |
| **Insights & administration** | Live dashboards, reports/exports, audit trail, permissions, MFA, privacy and legal-page management |

**Financial boundaries:** A recorded payment is not proof of bank settlement. Bank CSV imports require independent review and are not bank-authenticated; the current chart supports reconciliation for **one bank account** until a per-account subledger is implemented. MTN MoMo, Airtel Money and URA EFRIS adapters must stay disabled until each integration is verified and approved.

## Technology stack

| Layer | Technologies |
| --- | --- |
| **Frontend** | React 19, JavaScript/JSX, Vite 6, React Router 7, TanStack Query 5, Recharts 3, Lucide icons, responsive CSS/PWA |
| **API & business logic** | Python 3.12+, Flask 3, Flask-SQLAlchemy/SQLAlchemy, Flask-Migrate/Alembic, Gunicorn |
| **Database** | PostgreSQL 16+, psycopg 3; SQLite for explicitly isolated local preview/testing |
| **Task execution & rate limits** | PostgreSQL shared fixed-window limits for the Redis-free client demo; inline on-demand tasks; optional Celery/Redis for independently configured queued production jobs |
| **Security** | Argon2id passwords, JWT secure cookies with CSRF controls, role permissions, TOTP MFA, audited financial events, PostgreSQL RLS on selected private tables |
| **Files & integrations** | Optional S3-compatible private storage, ClamAV scanning, SMTP; gated MTN/Airtel/EFRIS adapters |
| **Deployment** | Docker Compose, Nginx static frontend, Caddy HTTPS edge or trusted Hostwares TLS proxy |
| **Quality** | pytest, Node.js tests, ESLint, Playwright/Chromium browser tests, GitHub Actions and PostgreSQL migration/invariant checks |

## Architecture

~~~mermaid
flowchart TB
    USERS["Owner · Staff · Tenants<br/>Desktop & mobile browsers"] --> EDGE["HTTPS edge<br/>Caddy or trusted Hostwares proxy"]
    EDGE --> WEB["Nginx · React/Vite build<br/>Static UI / PWA"]
    EDGE --> API["Gunicorn · Flask REST API<br/>Auth · RBAC · Business rules"]
    WEB -. "Same-origin /api/v1" .-> API
    API --> DB[("Private PostgreSQL<br/>business records · accounting · audit")]
    API --> LIMITS[("PostgreSQL shared limit counters<br/>Redis-free demo")]
    API -. "Optional external scheduler" .-> WORKER["Scheduled/queued jobs<br/>separate executor when enabled"]
    WORKER --> DB
    API -. "Configured, scanned storage only" .-> FILES["S3-compatible objects<br/>ClamAV"]
    API -. "Approved integrations only" .-> EXTERNAL["MTN / Airtel · URA EFRIS<br/>SMTP and other providers"]
~~~

The application is a **modular monolith**. Backend, workers, database and frontend are deployed as separate services, without introducing SaaS tenant provisioning or unnecessary microservices. API/database services are private; only the approved HTTPS ingress is public.

### Collections and accounting controls

~~~mermaid
flowchart TD
    LEASE["Approved lease"] --> INVOICE["Generate rent invoice"]
    INVOICE --> PENDING["Payment recorded as pending"]
    PENDING --> CHECK{"Independent staff approval<br/>or validated provider settlement"}
    CHECK -->|"Not verified"| HOLD["Remain pending · do not recognize as settled"]
    CHECK -->|"Verified"| RECEIPT["Reconciled payment + immutable accounting entry"]
    RECEIPT --> BANKCSV["Import actual bank statement CSV"]
    BANKCSV --> MATCH{"Independent match review<br/>and balance checks"}
    MATCH -->|"Exception"| REVIEW["Investigate mismatch; retain audit evidence"]
    MATCH -->|"Approved"| BANKGL["Move eligible cleared funds to BANK ledger"]
    BANKGL --> REPORT["Internal statements and reports"]
    REPORT -. "Only if approved and verified" .-> FISCAL["Applicable URA fiscalization"]
~~~

Financial history is corrected through controlled entries/reversals, not deletion. Actual bank authenticity, payment-provider callbacks, taxpayer-specific fiscal obligations and opening balances require independent validation.

## Local development (Windows / VS Code)

**Prerequisites:** Windows 10/11, VS Code, Python 3.12+, Node.js 22+ and local PostgreSQL 16+ for the preferred demo. Docker is **not required** for the normal local PostgreSQL demo, but is required for the full isolated test suite.

1. **First run only:** Open the repository in VS Code → **Terminal → Run Task → KATS: Setup demo once + Start Dev**. This prepares an isolated local PostgreSQL database and creates **1 owner + 30 fictional tenant accounts**.
2. **Every subsequent day:** Run **KATS: Start Dev (Frontend + Backend)**. It opens Flask and React in separate visible terminals and reuses existing data—**no reseeding, migration, package installation or build on daily startup**.
3. Open **http://127.0.0.1:5173** (frontend). Flask serves **http://127.0.0.1:8000**. Stop using the VS Code stop task or `.\stop.bat`; the database is preserved.

~~~mermaid
flowchart LR
    FIRST["First installation"] --> SETUP["One-time PostgreSQL setup<br/>migrations + fictional seed"]
    SETUP --> DEV["Start Flask + Vite"]
    NEXT["Later development sessions"] --> DEV
    DEV --> DATA[("Existing local data retained")]
~~~

See [Windows development](docs/NATIVE_DEVELOPMENT.md) and [local PostgreSQL demo](docs/LOCAL_POSTGRES_DEMO.md). **Never reuse demo accounts or fictional seed data in production.**

## Verification

From the repository root on Windows:

~~~powershell
.\tests\test-all.bat
~~~

The full suite needs Docker Desktop. For a quick frontend check:

~~~bash
cd frontend
npm ci
npm run build
~~~

GitHub Actions runs backend/API and migrated PostgreSQL checks, frontend/browser tests and Windows launcher tests for pull requests to `main` and pushes to `main`. See [test entry points](tests/README.md) and [go-live requirements](docs/GO_LIVE_CHECKLIST.md).

## Client review on Vercel (not the Hostwares launch)

The repository can be prepared as a **full-stack Vercel Services** project
(React frontend + Flask backend) for client acceptance against **fictional,
isolated** PostgreSQL data, using shared database-backed rate limits and no Redis for client review. The deployment must be under a Vercel plan
permitted for commercial client work; the connected Hobby team is not
sufficient for that use. No actual Vercel deployment or live URL is assumed.

Read **[Vercel client review setup](docs/VERCEL_CLIENT_PREVIEW.md)** and use
`ops/vercel.env.sample` as a key-name checklist only (never as real secrets).
The optional read-only live probe is
`python ops/verify_vercel_preview.py --url https://ACTUAL-VERCEL-REVIEW-HOST`.
Request-triggered demo jobs can run inline, but **scheduled jobs still require a separate approved scheduler**; an HTTP-only Vercel deployment does not run monthly/daily jobs automatically. Keep Hostwares as the separate
production system.

## Production and capacity

The baseline can serve a small single-owner operation **subject to real deployment and acceptance testing**. Tens of users are the expected use case; **hundreds of registered users are a capacity objective, not a tested guarantee**. Concurrent traffic, payment volume, report queries and background jobs determine actual limits.

Before launch or scaling:

- Provision private managed PostgreSQL, restricted DB roles, HTTPS, isolated secrets and durable storage as needed. Use a PostgreSQL-backed shared rate limiter for Redis-free deployments; add Redis/Celery only if the eventual queued-production architecture requires it.
- Verify backup **restoration**, rollback, migrations, MFA enrollment, role-level isolation and operational alerting in staging.
- Load-test authenticated owner, staff and tenant flows and payment concurrency; measure p95/p99 latency, errors, DB pool pressure, queue depth and resource use before raising worker counts.
- Complete provider sandbox/settlement acceptance, accountant reconciliation, legal/privacy review, real Android/iOS testing and owner signoff.

Start with the existing single-business architecture. Scale API replicas and optional worker replicas and tune SQL/indices **from measured bottlenecks**, maintaining a single scheduler and shared rate limiter. No production capacity or availability SLA has been established.

## Documentation

- **[Architecture](docs/ARCHITECTURE.md)** · **[Development](docs/NATIVE_DEVELOPMENT.md)** · **[Testing](tests/README.md)**
- **[Production deployment](docs/PRODUCTION_DEPLOYMENT.md)** · **[Hostwares runbook](docs/HOSTWARES_DEPLOYMENT.md)** · **[Security & performance](docs/PRODUCTION_PERFORMANCE.md)**
- **[Delivery status](docs/DELIVERY_STATUS.md)** · **[Operations](docs/OPERATIONS.md)** · **[Go-live checklist](docs/GO_LIVE_CHECKLIST.md)** · **[Presentation acceptance](docs/PRESENTATION_ACCEPTANCE.md)**

## Ownership & license

© 2026 **Kats Properties**. All rights reserved. This is proprietary, **not open-source**, software. Access to the repository does not grant permission to redistribute, license or resell it. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md). Third-party dependencies retain their own licenses.
