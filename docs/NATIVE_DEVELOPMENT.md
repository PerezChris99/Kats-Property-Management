# Native KATS management development (Windows + VS Code)

The public entry pages are **Home, Features, How It Works, About, and Request
Access**. Real daily management happens **after sign-in** in role-restricted
property, lease, rent, maintenance, reporting and administration workspaces.
Access requests are reviewed by an OWNER/SUPER_ADMIN, not registrations.

## Dedicated local service ports

React/Vite runs at `http://127.0.0.1:5173`; Flask runs separately at
`http://127.0.0.1:8000`. Both use one
[`ops/dev_ports.json`](../ops/dev_ports.json) configuration shared by the
Python launcher and Vite. `strictPort: true` blocks silent Vite fallback.
Frontend `/api`, `/readyz`, and `/healthz` proxy to Flask's dedicated
backend listener. Only valid, distinct ports are accepted, and both services
remain loopback-only. Production reverse-proxy routing is unaffected.

## VS Code development — one-time setup, then instant daily start

**After you've already seeded `kats_demo`, skip setup entirely.** In VS Code,
select **Terminal → Run Task → KATS: Start Dev (Frontend + Backend)**.

- Both integrated terminal panes open **immediately and in parallel**.
  **Left:** Flask on `127.0.0.1:8000`.
  **Right:** React/Vite on `127.0.0.1:5173`. The React pane displays a brief
  *waiting for Flask* message and launches Vite after the API is SQL-ready,
  so the browser does not get preventable proxy connection errors.
- Ordinary starts **do not seed, migrate, build, install packages, modify
  permissions, reset accounts or create a new database**. They only start
  the existing services against the restricted `kats_demo_runtime`
  PostgreSQL role. Existing properties, rent records and edited tenants are
  retained. The same ignored `.env.pg-demo` works even if the temporary
  `.local/dev-mode.json` file has been cleaned.
- If Flask cannot start, its own integrated terminal prints specific
  `[boot]` / `[ERROR]` messages, while the React terminal remains visible
  rather than being suppressed by a sequential VS Code task dependency.

**Only if you have never initialized this project:** choose
**KATS: Setup demo once + Start Dev**. This first-run task installs missing
dependencies, builds the frontend once, initializes the dedicated localhost
PostgreSQL `kats_demo` database, applies migrations/permissions, creates
**1 OWNER and 30 TENANT synthetic accounts**, then automatically opens the
same two dev terminals. The PostgreSQL administrator password is requested
only during the initial restricted-role bootstrap and is not persisted.

The separate **KATS: Dev prepare (PostgreSQL + seed 31 accounts)** task
performs preparation *without starting servers*, for advanced maintenance.
It is **never** a dependency of the daily Start Dev task.

**PostgreSQL is preferred.** SQLite is only a first-run fallback when
PostgreSQL is unavailable and no configured PostgreSQL demo exists; daily
startup cannot silently substitute SQLite for an established PostgreSQL
database. For an explicit local PostgreSQL-only setup, run
`$env:KATS_DEMO_DB='postgres'; .\\ops\\launch.bat dev-prepare` from a
PowerShell terminal, then use the ordinary Start Dev task.

Visit http://127.0.0.1:5173/login after startup. The login page reads the
active demo users through Flask and retries on transient errors. To verify,
run the **KATS: Verify frontend ↔ backend ↔ database** task or
`.\\ops\\launch.bat dev-doctor`.

### First-run PostgreSQL authorization

The bootstrap **only** connects to `127.0.0.1`. It asks for the PostgreSQL
administrator password *in the VS Code terminal* and uses it once to create
the named restricted database roles and `kats_demo`. The password is not
stored. Generated isolated runtime credentials are written to the git-ignored
`.env.pg-demo`; the system never touches other databases, destroys tables,
or connects to cloud/production databases for this workflow.

Later starts **only verify the database marker**; they do not run
migrations, seed scripts or permission commands. Existing edited records
are retained, including intentionally changed/inactivated demo profiles.
If a future application update introduces new schema migrations, run
`.\\ops\\local_pg_demo.bat upgrade` **explicitly once**, after a local
backup. This performs migrations and permissions only, not demo seeding.
For a deeper read-only seed/RLS audit, run
`.\\ops\\local_pg_demo.bat verify` (note: it checks the original exact
seed counts and can fail after intentional user edits).
The `.env.pg-demo` credentials and `.local/dev-mode.json` are never
committed. A missing temporary mode file is recovered from the validated,
existing PostgreSQL configuration without rerunning setup or seeding.

By default no environment setting is needed. To **force PostgreSQL**
without allowing fallback, use an integrated PowerShell terminal to initialize
it once, then use the **KATS: Start Dev (Frontend + Backend)** task:

```powershell
$env:KATS_DEMO_DB = 'postgres'
.\\ops\\launch.bat dev-prepare
Remove-Item Env:KATS_DEMO_DB -ErrorAction SilentlyContinue
```

For intentional SQLite-only development, use
`$env:KATS_DEMO_DB='sqlite'` for that preflight command. Variables set in
a terminal do **not** automatically change the environment of VS Code Tasks
launched by VS Code; the one-time setup task uses its own default PostgreSQL-first auto-selection;
regular Start Dev does not run setup or database selection.

For custom PG ports use `KATS_PG_DEMO_PORT` before first setup. If already
configured, update the ignored configuration deliberately; the launcher
refuses unrelated database owners or mismatched instance markers.

Existing test/workflow options are retained: **KATS: PostgreSQL demo
verify (counts, RLS and logins)** performs an exact clean-demo integrity
audit; **KATS: Demo start (landlord + 30 tenants)** remains an explicit
SQLite preview mode; and **KATS: Native setup (database + build)** retains
the older isolated Docker/SQLite developer workflow. The ordinary
**KATS: Start Dev** task uses local PostgreSQL as its first choice.

### Stopping and restarting

Stop via **KATS: Stop (preserve database)** or `.\stop.bat`; this keeps both
the `kats_demo` PostgreSQL database and the SQLite fallback intact.
Do not run two backends against port 8000 while changing database modes.
If port 8000 is already occupied, the unified task stops with a useful error
rather than silently attaching to a different database.

**Note:** The root `.\start.bat` remains the legacy *external Windows
Terminal* launcher; choose the VS Code **Start Dev** task to use the complete
combined PostgreSQL/seed workflow without leaving VS Code.

## Start both services when Flask is already running

For the combined PostgreSQL/demo task, first stop an already running
KATS backend to avoid mixing the new demo session with a previous database.
Standalone native frontend/backend launchers can still reuse an existing
healthy service without disturbing it.

The launcher checks both local ports first. If it recognizes an existing
healthy KATS Flask endpoint, it **reuses that backend** and starts only
the missing React/Vite frontend on `127.0.0.1:5173`. It also handles
the reverse situation (frontend already running) and avoids running
setup or migrations against the reused backend. Foreign or unhealthy
processes occupying those ports are never killed or silently reused.

The terminal will report `React ... (started)`, `Flask ... (existing)`
and `[CONNECTED]` once React's API proxy reaches Flask and SQL.
Use **http://127.0.0.1:5173** to open the UI, **not** port 8000;
port 8000 is exclusively the API backend. Logs from reused processes
remain in their original terminal. Logs from newly launched processes
stream into the current VS Code terminal.

If you only want to add the UI without re-running the combined launcher,
you can also use **KATS: Native frontend (BAT)** in VS Code or
`.\start-frontend.bat` in PowerShell from the repository root.
Use **KATS: Stop (preserve database)** to stop both native launchers.

## If VS Code reports "task errors" or startup takes minutes

Previous KATS task definitions used an invalid VS Code problem matcher
(`regexp: "a^"` with no file/line/message captures), and older startup
tasks silently required Docker even when using the preview. Both defects
are corrected. The default Start Dev task waits for the backend background task's real [READY] signal before starting the frontend task, each with a valid VS Code problem matcher and live logs.

1. After pulling the updated source, run **Developer: Reload Window**
   in VS Code to discard old task definitions.
2. Open the **repository root folder**, not just `frontend` or `backend`.
3. Start the app using the task **KATS: Start Dev (Frontend + Backend)**.
   If dependencies are installed, the servers start directly. Otherwise the relevant terminal reports exactly which setup task to run.
4. Look for `[READY]` and `[CONNECTED]`. If they do not appear, copy the
   **first** `[ERROR]` line and its preceding diagnostic from the terminal.
5. Run `KATS: Verify frontend ↔ backend ↔ database` only after both servers
   have started; this check is not a substitute for launching the app.

The combined PostgreSQL demo Start Dev task now performs an idempotent build,
setup and seed preflight. The older `KATS: Native setup (database + build)` remains
available for the separate legacy Docker/SQLite workflow. **A full setup may legitimately take several minutes**
on a first install, but it no longer runs on every ordinary startup.
Legacy Docker-only setup/launch/log tasks were removed from the VS Code
task picker to prevent misleading errors when Docker is absent.

## Full local infrastructure

Docker is optional for the preview but required by the built-in full
PostgreSQL/Redis stack. With Docker Desktop installed/running, the default
native launcher starts isolated local-only PostgreSQL and Redis containers,
runs Alembic migrations, seeds permissions and starts API + Celery worker
and Beat. Ports are loopback-only. It does not use your production DB.

The VS Code **KATS: Test frontend + API + backend + PostgreSQL**, isolated
browser E2E and recovery checks depend on Docker where documented; CI runs
its own disposable PostgreSQL and browser runtime.

## Graceful shutdown, logs and recovery

- In the running integrated terminal, **Ctrl+C** requests a Windows
  `CTRL_BREAK_EVENT` for the launcher-managed Node/Python process groups.
  A bounded wait allows normal exit; forced termination is a last resort.
- **KATS: Native stop dependencies (BAT)** or `stop.bat` asks all native
  launchers to exit via an ignored local stop marker before stopping native
  Docker services. Volumes and the isolated SQLite database are retained.
  Avoid using Task Manager unless normal shutdown fails.
- Browser and API logs stream into separate VS Code terminals, prefixed with service names.
  There is **no automatic persistent log of sensitive request paths or
  credentials**. Do not paste tenant tokens or secrets into bug reports.
- A stale stop marker is ignored by new runs because each launcher compares
  the marker timestamp with its own start time.
- If Vite reports a proxy error, inspect the backend pane, confirm SQL
  readiness, and rerun the connection-check task. If a service exits early,
  the launch task reports its exit code instead of silently claiming ready.

## Production boundaries

The production deployment is not the SQLite preview. It requires managed
private PostgreSQL/Redis, TLS, a restricted database runtime role, schema
migrations and backups. Run `python -m app.release_preflight` inside the
deployed **API container**, after the operator-approved migration step.
Preflight is read-only and fails on invalid production settings, schema,
database role/RLS or Redis. A passing preflight is **not** a release
approval: external payment/fiscal providers, storage scanner, real backup
restore, live legal pages and role-by-role acceptance still require
independent evidence. See [Production deployment](PRODUCTION_DEPLOYMENT.md)
and [Go-live checklist](GO_LIVE_CHECKLIST.md).
