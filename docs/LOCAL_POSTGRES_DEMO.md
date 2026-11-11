# KATS — local PostgreSQL demonstration (no Docker)

This creates a **separate local database named `kats_demo`**, not the existing
`kats_native`, `kats_ci`, `ProcurePilot`, or any remote PostgreSQL/Neon
database. The dataset is fictional; do not use it for real payments.

## What you need

- Windows 10/11, VS Code, Python 3.12+ and Node.js 22+.
- A running local PostgreSQL 16/17+ server listening on **127.0.0.1:5432**.
- The existing local PostgreSQL administrator account (normally `postgres`)
  password for the *first* setup only. It is prompted, never saved or committed.
- **Docker is not required** to run this database or the local demo. The
  repository's *full* isolated automated test suite still requires Docker.

To inspect your installed Windows PostgreSQL service, use
`Get-Service *postgres*`. If it is stopped and you have Windows administrator
access, start the existing service using Services or `Start-Service` with its
actual service name. Nothing in this setup starts, reconfigures or overwrites
the PostgreSQL server itself.

If PostgreSQL uses another local port, set
`$env:KATS_PG_DEMO_PORT='5433'` *before the first setup*.

## One-time setup from PowerShell

Open the repository root in VS Code, then run:

~~~powershell
cd "D:\NEW PROJECTS\Kats-Property-Management"
git checkout perez
git pull --ff-only origin perez
.\ops\local_pg_demo.bat setup
~~~

Or use **Terminal → Run Task → KATS: PostgreSQL demo setup (31 accounts)**.

The setup script:

1. Creates ignored `.env.pg-demo` with independent 32+-character local
   credentials and a unique instance identifier.
2. Connects **only** to the PostgreSQL service at 127.0.0.1. It asks for the
   local administrator password without storing or logging it.
3. Creates the isolated database `kats_demo`, schema owner
   `kats_demo_owner` and non-superuser runtime `kats_demo_runtime`. If a
   database exists without the matching instance marker, it refuses access.
   **No database is ever dropped or overwritten.**
4. Runs all Alembic migrations, seeds role permissions and the complete
   fictional landlord/tenant portfolio using the owner role and explicit
   service RLS context.
5. Grants the limited runtime role, verifies real forced PostgreSQL RLS,
   entity counts, foreign-key relationships and real Flask landlord/tenant
   login + forbidden cross-role access.
6. Leaves data available for subsequent sessions. Re-running setup checks
   existing sample accounts instead of resetting them.

### Expected verified seed counts

| Record | Expected count |
|---|---:|
| Login accounts | 31 (1 OWNER, 30 TENANT) |
| Linked tenant profiles | 30 |
| Active leases | 30 |
| Properties / buildings / floors | 3 / 3 / 9 |
| Rooms | 33 (30 occupied; 3 vacant) |
| Rent invoices / invoice lines | 60 / 60 |
| Reconciled sample payments | Generated according to the existing synthetic billing scenarios |
| Maintenance requests | 4 |

Expected counts are automatically checked against the *actual local database*
on setup and verification, rather than assumed.

## Start the actual PostgreSQL-backed demo

Use **Terminal → Run Task → KATS: PostgreSQL demo start (31 accounts)**.
This starts separate Flask and Vite terminals within VS Code.

Alternatively use two PowerShell terminals:

~~~powershell
# Terminal 1
.\ops\local_pg_demo.bat serve

# Terminal 2 (after initializing normal frontend dependencies once)
.\start-frontend.bat
~~~

Open **http://127.0.0.1:5173/login**. Under the local demo selector, choose
**Landlord workspace** or any of 30 tenant accounts (on phones, expand the
demo panel). Each click issues an ordinary audited, revocable authenticated
session; no reusable demo password is embedded in the browser. Unlike the
SQLite preview, data is stored in PostgreSQL and its forced row-level
security policies are active.

Verify at any time:

~~~powershell
.\ops\local_pg_demo.bat verify
~~~

Or **Tasks → KATS: PostgreSQL demo verify (counts, RLS and logins)**.

To stop, press **Ctrl+C** in each running integrated terminal or use the
normal KATS stop task. The PostgreSQL service and `kats_demo` contents
are preserved; the app must not terminate your shared Windows PostgreSQL
service.

## Safety constraints

- Never commit `.env.pg-demo`. Its credentials and instance marker are
  intentionally ignored by Git.
- Demo endpoints require **development mode**, a local-only database,
  the correct named restricted SQL role, a matching random database marker,
  local HTTP Host, and a loopback client address. Remote/production environments
  cannot enable demo account shortcuts by simply changing a URL.
- All real payment/EFRIS, SMS/email and external storage providers are disabled.
  Redis and Celery use local development-only in-memory/eager settings. They are
  **not** substitutes for production workers, shared rate limiting or backups.
- The database is separate from the PostgreSQL instance's other databases.
  Do not use PgAdmin's *drop database* command to troubleshoot.
- To run **every existing automated test**, install/start Docker Desktop and
  run `.\tests\test-all.bat`. That suite uses isolated `kats_ci` and E2E
  databases; it does **not** run destructive tests against `kats_demo`.
  For fast code-only checks without Docker:
  `.\tests\test-frontend.bat`, `.\tests\test-backend.bat`,
  `.\tests\test-api.bat`, `.\tests\test-security.bat`.

## Test log diagnosis (11 November 2026)

The supplied Windows log shows frontend **38/38 tests passed** and its
production bundle built, backend **177 passed / 4 skipped**, 76% overall
Python line coverage. Configuration, PostgreSQL integration and E2E failed
solely because the `docker` CLI was unavailable. Smoke failed because
nothing listened at localhost:5173. There was also a Python 3.14 invalid
escape warning (now fixed) and an intermittent sqlite3 ResourceWarning;
neither was a test failure. The external staging load and live provider
tests were not run. Docker-free demo bootstrapping does *not* silently
relabel those tests as passed.
