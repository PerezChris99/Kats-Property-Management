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

## One-command development: local PostgreSQL + demo accounts + React/Flask

**Recommended default:** Open the repository root in VS Code, ensure Python
3.12+, Node 22+ and your installed **PostgreSQL 17** (or compatible version)
are available. From **Terminal → Run Task**, choose:

**KATS: Start Dev (Frontend + Backend)**

This single task runs sequential preflight, then launches two live integrated
terminals in parallel:

1. **Prepare:** install missing Python/npm dependencies; run the React JSX,
   lint, unit-test and Vite build; find a PostgreSQL server on localhost
   (default TCP port `5432`, override via `KATS_PG_DEMO_PORT` on first run).
2. **If PostgreSQL is reachable:** initialize the isolated `kats_demo`
   database (first run requires the *local* PostgreSQL admin password), run
   Alembic migrations, seed route permissions, create and validate 31
   synthetic accounts (**1 OWNER + 30 TENANT**), and preserve subsequent user
   edits. The account picker enables direct demo sign-in. The application's
   runtime uses `kats_demo_runtime`, which is not a PostgreSQL superuser and
   cannot bypass RLS. This uses installed local PostgreSQL, **not SQLite or
   Docker's parallel `kats_native` database**.
3. **If PostgreSQL is unreachable:** visibly report **SQLite FALLBACK**,
   initialize only `.local/kats-preview.sqlite3`, seed the same 31 demo
   accounts and launch the app. This mode has no PostgreSQL RLS or full Celery
   infrastructure. **If PostgreSQL is listening but passwords, marker,
   migration or seeding fail, startup stops instead of silently changing DBs.**
4. **Start:** Flask/backend runs in the **left** VS Code integrated terminal
   and React/Vite in the **right**, both with live logs. Open
   http://127.0.0.1:5173. The original secure login and 31-account local
   demo selector remain available.
5. **Verify:** Run task **KATS: Verify frontend ↔ backend ↔ database**.
   It checks the Vite → Flask SQL bridge, protection of anonymous sessions,
   and all 31 demo accounts.

### First-run PostgreSQL authorization

The bootstrap **only** connects to `127.0.0.1`. It asks for the PostgreSQL
administrator password *in the VS Code terminal* and uses it once to create
the named restricted database roles and `kats_demo`. The password is not
stored. Generated isolated runtime credentials are written to the git-ignored
`.env.pg-demo`; the system never touches other databases, destroys tables,
or connects to cloud/production databases for this workflow.

Later starts verify the database marker and idempotently check the
**existing** demo records without overwriting passwords or operator changes.
Partially damaged demo datasets fail safely rather than being silently repaired.
The `.env.pg-demo` credentials and `.local/dev-mode.json` are never
committed. The backend refuses an unprepared or wrong database mode.

By default no environment setting is needed. To **force PostgreSQL**
without allowing fallback, use an integrated PowerShell terminal and prepare
there first, then run the **KATS: Dev services (split in VS Code)** task:

```powershell
$env:KATS_DEMO_DB = 'postgres'
.\\ops\\launch.bat dev-prepare
Remove-Item Env:KATS_DEMO_DB -ErrorAction SilentlyContinue
```

For intentional SQLite-only development, use
`$env:KATS_DEMO_DB='sqlite'` for that preflight command. Variables set in
a terminal do **not** automatically change the environment of VS Code Tasks
launched by VS Code; the regular combined Start Dev task instead uses its
own default PostgreSQL-first auto-selection.

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
are corrected. The default Start Dev task runs two independent background tasks in parallel, each with a valid VS Code problem matcher and live logs.

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
