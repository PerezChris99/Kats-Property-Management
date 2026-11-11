# Native KATS management development (Windows + VS Code)

The public entry pages are **Home, Features, How It Works, About, and Request
Access**. Real daily management happens **after sign-in** in role-restricted
property, lease, rent, maintenance, reporting and administration workspaces.
Access requests are reviewed by an OWNER/SUPER_ADMIN, not registrations.

## First-time setup, without Docker

1. Open the repository in VS Code. Ensure Python 3.12+ and Node 22+ are on PATH.
2. **Once per checkout or after requirements change:** **Tasks: Run Task → KATS: Native setup (database + build)**. It creates
   an ignored local secrets file, installs Python/Node dependencies, builds
   the React app, creates the isolated local SQLite schema and seeds role
   permissions. It never overwrites an existing database or production .env.
3. **Tasks: Run Task → KATS: Start Dev (Frontend + Backend)**.
   This starts both applications **in one reliable VS Code integrated
   terminal**. Live output is labeled `[React]` and `[Flask]` for clarity.
   It **does not run a full Vite release build or repeat pip/npm installation**
   when requirements have not changed. For two separate terminal panes, use
   `KATS: Native start (split in VS Code)` (the task matchers are valid).
   In full PostgreSQL mode, worker/Beat output is also labeled and visible.
4. **Tasks: Run Task → KATS: Verify frontend ↔ backend ↔ database**.
   The check requires JSON `status=ready` and Flask's `X-Request-ID` from
   `http://127.0.0.1:5173/readyz`, then confirms the direct Flask SQL
   readiness at `:8000/readyz` and an HTTP 401/422 from proxied
   unauthenticated `/api/v1/auth/me`. A Vite HTML 200 cannot pass.
5. Open `http://localhost:5173`. Owner creation is a separate privileged
   operation: **KATS: Native create owner (BAT)**.

Local settings and the SQLite database stay in ignored `.env.native` and
`.local/kats-preview.sqlite3`. The preview mode **is not equivalent to
production**: SQLite does not enforce PostgreSQL RLS and background Celery
scheduling/payment-provider integrations are inactive. Financial workflows
must not be considered operationally accepted in preview mode.

## Start both services when Flask is already running

Use **Tasks: Run Task → KATS: Start Dev (Frontend + Backend)**, even if
an older KATS Flask process is already active at `127.0.0.1:8000`.

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
are corrected. The **default Start Dev task is a foreground process**, not
a background task depending on invalid watchers. It keeps running to
display live logs.

1. After pulling the updated source, run **Developer: Reload Window**
   in VS Code to discard old task definitions.
2. Open the **repository root folder**, not just `frontend` or `backend`.
3. Start the app using the task **KATS: Start Dev (Frontend + Backend)**.
   If dependencies were already installed, it starts Vite and Flask directly.
   If they are missing, only those dependencies are installed.
4. Look for `[READY]` and `[CONNECTED]`. If they do not appear, copy the
   **first** `[ERROR]` line and its preceding diagnostic from the terminal.
5. Run `KATS: Verify frontend ↔ backend ↔ database` only after both servers
   have started; this check is not a substitute for launching the app.

Use `KATS: Native setup (database + build)` only initially or to explicitly
run the build/tests. **A full setup may legitimately take several minutes**
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
- Browser/API logs are printed live in the main VS Code terminal, prefixed with service names.
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
