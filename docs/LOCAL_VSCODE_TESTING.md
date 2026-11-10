# KATS — VS Code local test and acceptance guide

For individual CMD/PowerShell batch launchers for every test category and the one-command full local suite, see [Windows test commands](WINDOWS_TEST_LAUNCHERS.md). Use test-all.bat in CMD or .\test-all.bat in PowerShell. Approved external staging load tests remain separate.

For the **native Python virtualenv and React launch from CMD/PowerShell .bat files**, see the [Windows batch launcher guide](WINDOWS_BATCH_LAUNCHERS.md). The Docker-based acceptance commands below remain independent; never launch both application variants on 5173/8000 together.

**Source:** Kats Property Management · **State:** local code verification, not business go-live

This guide runs the actual React/JSX UI, Flask API, Celery/Redis and PostgreSQL
through **VS Code integrated terminals** on Windows. It uses the existing
repository's `perez → main` flow and does not require external terminal windows.

## 1. First-time developer setup

Prerequisites: Windows 10/11, VS Code, Git, Docker Desktop with Linux containers
and Compose, PowerShell, and Python 3.12+ (for Chromium browser automation).
Start Docker Desktop before executing commands.

Open the repository folder in VS Code, then choose
**Terminal → Run Task → KATS: Setup**. Or in the VS Code PowerShell terminal:

~~~powershell
.\ops\dev.ps1 -Action setup
~~~

The setup creates a gitignored local `.env` from `.env.example` if missing,
with freshly generated unrelated 256-bit application/JWT secrets. It **does not**
overwrite existing environment files. The example database password is for
isolated localhost development only, never a public service.

For the complete application:

~~~powershell
.\ops\dev.ps1 -Action start
~~~

This builds and starts the Docker stack; runs Alembic migrations and seeds
permissions; then checks the landing page, API readiness and anonymous denial.
The app is at **http://localhost:5173**. The API readiness probe is available at
**http://localhost:8000/readyz**.

Create the **first owner**, if no owner exists, in a VS Code integrated terminal:

~~~powershell
.\ops\dev.ps1 -Action owner
~~~

This command prompts interactively; do not copy passwords into source, scripts,
screenshots or test results. Subsequent staff/tenant accounts should use the
authorized application invitation process.

## 2. One-command automatic acceptance

~~~powershell
.\ops\dev.ps1 -Action all
~~~

Or choose **Terminal → Run Task → KATS: Full local acceptance**. This executes:

| Gate | What runs | Data protection |
| --- | --- | --- |
| Startup | Docker builds, service startup, migrations, permission seeding | Operational local DB preserved |
| Frontend | `npm ci` + JSX-only check + ESLint + Node API tests + Vite production build | Build-time only |
| Backend | Python pytest suite plus Flask compilation | SQLite fixtures and isolated test PostgreSQL |
| PostgreSQL | Full Alembic upgrade, restricted document RLS, concurrent financial posting | **Disposable test-db/kats_ci only** |
| HTTP | Landing availability, SQL readiness, unauthenticated access denial | Read-only |
| Browser | Chromium public navigation, 360/768/1440 viewport, private route redirects, six real test-role sessions | Separate disposable Compose stack |
| Optional roles | Authenticated owner portal navigation when E2E test credentials provided | Read-only; local credentials only |

Only `test-db` is deleted/recreated for the PostgreSQL suite; it uses an
in-memory PostgreSQL volume with **no host port** and separate credentials.
The regular `db` service and its persistent volumes are never reset by tests.
Do not copy production data into the test container.

## 3. Individual checks in VS Code

~~~powershell
# Full backend, frontend and PostgreSQL suite (no need to start UI):
.\ops\dev.ps1 -Action test

# HTTP API/landing smoke against a running localhost stack:
.\ops\dev.ps1 -Action smoke

# Playwright Chromium: requires running localhost UI and Python 3.12+:
.\ops\dev.ps1 -Action browser

# Observe containers and logs:
.\ops\dev.ps1 -Action status
.\ops\dev.ps1 -Action logs

# Stop services but PRESERVE live local database volumes:
.\ops\dev.ps1 -Action stop
~~~

All scripts return nonzero on failures; **do not merge** when a gate fails.
If Docker fails to start, verify Docker Desktop virtualization, free disk,
Docker WSL integration, port ownership (5173 and 8000) and local `.env`.
Use `docker compose logs --tail=100 api web worker beat db redis` to diagnose.

For direct native frontend debugging, with Node 22 installed:

~~~powershell
cd frontend
npm ci
npm run lint
npm test
npm run build
npm run dev
~~~

The Docker web service serves a compiled app and **does not hot reload**. Stop
the Docker web service before starting the native Vite dev server on 5173.
Vite's default dev proxy is not configured in this repository; prefer Docker's
integrated Nginx app for cross-layer browser acceptance.

## 4. Fully isolated six-role browser acceptance

The **recommended real-browser test** starts a separate Docker Compose project
with temporary PostgreSQL/Redis and its own localhost-only browser port. It
generates fresh random secrets and creates six synthetic local accounts:
OWNER, SUPER_ADMIN, MANAGER, ACCOUNTANT, CARETAKER and TENANT. These accounts
are linked to a sample fictional rental, invoice and maintenance ticket.

~~~powershell
.\ops\dev.ps1 -Action browser-full
~~~

This exercises responsive public pages, API protections, session login and
role-specific portals at **http://localhost:5174** without requiring any real
business credentials. The whole E2E environment is removed after the test,
with no test data left in the normal application's database. The E2E database
uses PostgreSQL tmpfs and has no published port.

Use VS Code **Terminal → Run Task → KATS: Isolated six-role browser E2E**.
The full command `.\ops\dev.ps1 -Action all` includes this isolated test.

## 5. Optional tests against your existing local accounts



By default the browser suite runs without staff credentials. To enable role-scoped
navigation coverage, set **local** process environment variables in the VS Code
terminal (never commit them). The example below uses the owner role:

~~~powershell
$env:KATS_E2E_OWNER_EMAIL = 'your-local-test-owner@example.test'
# Paste only in this local terminal, with echo suppression if possible:
$ownerPassword = Read-Host 'Local test owner password' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($ownerPassword)
try { $env:KATS_E2E_OWNER_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
# Only if MFA is enabled, enter the current 6-digit code just before the test:
# $env:KATS_E2E_OWNER_TOTP = Read-Host 'Current authenticator code'
.\ops\dev.ps1 -Action browser
Remove-Item Env:KATS_E2E_OWNER_EMAIL,Env:KATS_E2E_OWNER_PASSWORD -ErrorAction SilentlyContinue
Remove-Item Env:KATS_E2E_OWNER_TOTP -ErrorAction SilentlyContinue
~~~

For other roles, set the same variables using the suffixes MANAGER, ACCOUNTANT,
CARETAKER, TENANT or SUPER_ADMIN, for example `KATS_E2E_TENANT_EMAIL` and
`KATS_E2E_TENANT_PASSWORD`. If MFA is enabled, provide the current one-time
`KATS_E2E_TENANT_TOTP` code (or equivalent role suffix) just before execution.
The tests verify the authenticated role and prevent caretaker/tenant access
to the administrator audit API.

Use **local disposable accounts**, never live users' passwords. Tests currently
verify basic portal navigation, not every create/update/delete transaction.
Those mutations must be approved and tested separately on an isolated dataset.

## 6. Manual role-based acceptance matrix

Record actual evidence for each role in a local issue/test record. Do not
write private data or passwords into Git.

| Area | Owner/manager/accountant | Caretaker | Tenant | Required acceptance evidence |
| --- | --- | --- | --- | --- |
| Identity | Owner invite, activation, reset, MFA, permissions | Scoped login/session | Tenant invitation and login | Invalid/cross-role access denied |
| Portfolio | Create/edit property, building/floor/room, archive | Assigned rooms only | Own leased room only | Reconciliation and audit trail |
| Lease lifecycle | Draft, legal review, renew, notice, end tenancy | Inspection access | Own lease and notice | Signed contract and delivery proof |
| Billing | Full/partial rent, invoices, credits | No unauthorized issuance | Own invoice, correct balance | No overlaps or double posting |
| Collections | Cash/bank maker/checker, reversal | Limited entrusted collection | Own payment history | Actual bank/provider reconciliation |
| Deposits | Hold/withhold/refund approvals | Inspection evidence | Own deposit and dispute | Actual payout and signed move-out |
| Utilities | Tariff, meter approval, invoice posting | Assigned meter readings | Own consumption and charges | Physical meter/tariff evidence |
| Maintenance | Review tickets, recurrence, closure | Assigned work orders | Submit own repair | One task per due date, evidence |
| Disputes | Review, comment, resolve/reopen | Restricted | Own current/former lease cases | Legal procedure and escalation |
| Exports | Restricted finance reports and PDF | Only authorized receipts | Own statement/receipts | Reconcile to SQL and physical cash |
| Privacy/documents | DSAR review, secure object storage | Assigned-only | Own file and privacy requests | Scanner, storage and legal obligations |
| Platform | Logs, backup, rate limit, dashboard | No admin privileges | No admin privileges | 3G/low-end phone, Firefox/Chrome/Safari |

For each workflow exercise good input, invalid input, empty state, duplicates,
concurrency, reconnection, role denial, pagination, keyboard/mobile layout,
timezones, and eventual reversal where legally permitted.

## Authorized performance measurements (staging only)

For load testing, use an **approved staging HTTPS host**, never your live
rent/payment environment or third-party payment gateway. Install k6 locally
and explicitly authorize the target before running:

~~~powershell
$env:KATS_LOAD_TEST_APPROVED = 'yes'
$env:BASE_URL = 'https://your-approved-staging-host.example'
k6 run ops/load-test.js
Remove-Item Env:KATS_LOAD_TEST_APPROVED,Env:BASE_URL -ErrorAction SilentlyContinue
~~~

The baseline measures read-only public APIs and reports p95/p99 latency and
error thresholds. It **does not** establish authenticated high-volume billing
performance or real-provider safety. Check PostgreSQL connection limits,
slow-query plans, lock waits, Celery queue depth, concurrent access,
memory/CPU, and realistic tenant/owner usage before changing production sizes.

## 7. Gates that local tests CANNOT close

The current application still lacks or has unverified code for contract
signature/delivery proof, advance-rent and multi-invoice allocation, full
double-entry ledger/bank reconciliation, real disbursements, provider-specific
fiscal credits, full data-subject-rights fulfillment, vendor purchasing and
certain agency/utility workflows. They remain **development work**, not merely
credentials or server hosting.

Separately, real MTN/Airtel merchant approval, URA EFRIS taxpayer-specific
connectors, SMTP deliverability, S3/ClamAV, domain/TLS, monitoring, backup
restore, legal approvals, external penetration/load testing and human field
UAT require evidence outside source code. See `UGANDA_AUTOPILOT_REGISTER.md`
and `GO_LIVE_CHECKLIST.md`. A green CI run is not a commercial go-live signoff.

No automated browser suite can prove every operational combination has been
exercised. Record failures and close them with reproducible regression tests.
