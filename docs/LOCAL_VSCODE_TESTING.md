# KATS — VS Code local test and acceptance guide

**Source:** Kats Property Management · **State:** local code verification, not business go-live

This guide runs the actual React/JSX UI, Flask API, Celery/Redis and PostgreSQL
through **VS Code integrated terminals** on Windows. It uses the existing
repository's \`perez → main\` flow and does not require external terminal windows.

## 1. First-time developer setup

Prerequisites: Windows 10/11, VS Code, Git, Docker Desktop with Linux containers
and Compose, PowerShell, and Python 3.12+ (for Chromium browser automation).
Start Docker Desktop before executing commands.

Open the repository folder in VS Code, then choose
**Terminal → Run Task → KATS: Setup**. Or in the VS Code PowerShell terminal:

~~~powershell
.\ops\dev.ps1 -Action setup
~~~

The setup creates a gitignored local \`.env\` from \`.env.example\` if missing,
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
| Frontend | \`npm ci\` + JSX-only check + ESLint + Node API tests + Vite production build | Build-time only |
| Backend | Python pytest suite plus Flask compilation | SQLite fixtures and isolated test PostgreSQL |
| PostgreSQL | Full Alembic upgrade, restricted document RLS, concurrent financial posting | **Disposable test-db/kats_ci only** |
| HTTP | Landing availability, SQL readiness, unauthenticated access denial | Read-only |
| Browser | Chromium public navigation, 360/768/1440 viewport, protected route redirects and API security | Read-only |
| Optional roles | Authenticated owner portal navigation when E2E test credentials provided | Read-only; local credentials only |

Only \`test-db\` is deleted/recreated for the PostgreSQL suite; it uses an
in-memory PostgreSQL volume with **no host port** and separate credentials.
The regular \`db\` service and its persistent volumes are never reset by tests.
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
Docker WSL integration, port ownership (5173 and 8000) and local \`.env\`.
Use \`docker compose logs --tail=100 api web worker beat db redis\` to diagnose.

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

## 4. Authenticated, non-destructive browser testing

By default the browser suite runs without staff credentials. To enable owner
navigation coverage, set **local** process environment variables in the VS Code
terminal (never commit them):

~~~powershell
$env:KATS_E2E_OWNER_EMAIL = 'your-local-test-owner@example.test'
$env:KATS_E2E_OWNER_PASSWORD = Read-Host 'Local test owner password'
# Only if MFA is enabled, enter the current 6-digit code just before the test:
# $env:KATS_E2E_OWNER_TOTP = Read-Host 'Current authenticator code'
.\ops\dev.ps1 -Action browser
Remove-Item Env:KATS_E2E_OWNER_EMAIL,Env:KATS_E2E_OWNER_PASSWORD -ErrorAction SilentlyContinue
Remove-Item Env:KATS_E2E_OWNER_TOTP -ErrorAction SilentlyContinue
~~~

Use a **local disposable account**, not a live user's password. Tests currently
verify basic portal navigation, not every create/update/delete transaction.
Those mutations must be approved and tested separately on an isolated dataset.

## 5. Manual role-based acceptance matrix

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

## 6. Gates that local tests CANNOT close

The current application still lacks or has unverified code for contract
signature/delivery proof, advance-rent and multi-invoice allocation, full
double-entry ledger/bank reconciliation, real disbursements, provider-specific
fiscal credits, full data-subject-rights fulfillment, vendor purchasing and
certain agency/utility workflows. They remain **development work**, not merely
credentials or server hosting.

Separately, real MTN/Airtel merchant approval, URA EFRIS taxpayer-specific
connectors, SMTP deliverability, S3/ClamAV, domain/TLS, monitoring, backup
restore, legal approvals, external penetration/load testing and human field
UAT require evidence outside source code. See \`UGANDA_AUTOPILOT_REGISTER.md\`
and \`GO_LIVE_CHECKLIST.md\`. A green CI run is not a commercial go-live signoff.

No automated browser suite can prove every operational combination has been
exercised. Record failures and close them with reproducible regression tests.
