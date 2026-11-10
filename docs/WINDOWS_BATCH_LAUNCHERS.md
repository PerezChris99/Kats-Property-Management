# KATS — Windows batch launchers

Use the batch files from the **repository root**, inside the VS Code integrated
terminal. They work in CMD and PowerShell without changing PowerShell's
execution policy, and they do **not open additional terminal windows**.

## Prerequisites

Windows 10/11, VS Code, Python 3.12+, Node.js 22+ (including npm), Git,
and Docker Desktop running Linux containers. Docker is needed only for the
development PostgreSQL and Redis dependencies, not to build React or Flask.

## One command to start the application

**CMD**

~~~cmd
start.bat
~~~

**PowerShell**

~~~powershell
.\start.bat
~~~

The script performs these actions in order:

1. Detects a compatible Python installation, Node 22+ and npm.
2. Installs locked Node dependencies when missing or changed.
3. Executes npm run build, including JSX checks, ESLint, and JavaScript tests.
4. Finds the repository root .venv or creates it using Python 3.12+.
5. Detects whether the project virtual environment was already active. If
   not, it configures VIRTUAL_ENV, PATH and the exact venv Python executable
   for the backend child processes. This achieves normal virtualenv activation
   inside those processes without modifying the calling PowerShell session.
6. Executes python -m pip install -r backend/requirements.txt inside the venv.
7. Generates a gitignored .env.native with fresh secrets if missing. It never
   replaces an existing file.
8. Starts a dedicated kats-native Docker Compose project with PostgreSQL 16
   and Redis, isolated from the normal application database.
9. Runs Alembic database migrations and seeds default role permissions.
10. Starts React (Vite), Flask, a Windows-compatible Celery solo worker and
    one Celery Beat scheduler, with logs in the current integrated terminal.
11. Verifies the frontend and backend readiness. Press Ctrl+C to stop the
    launched application processes. PostgreSQL data is preserved.

Vite builds successfully before startup but then runs in hot-reload
development mode. To serve production-built static assets, use the separate
existing Docker web application instead of Vite's development server.

## Individual launch commands

| Task | CMD | PowerShell |
| --- | --- | --- |
| Entire application | start.bat | .\start.bat |
| React only (build and run) | start-frontend.bat | .\start-frontend.bat |
| Flask only (prepare venv, install, migrate, run) | start-backend.bat | .\start-backend.bat |
| Create owner interactively | create-owner.bat | .\create-owner.bat |
| Stop local database and Redis | stop.bat | .\stop.bat |

The React-only command expects an existing backend for authenticated data.
The Flask-only command does not also launch Celery; the full start command
does. If you launch both standalone scripts, use separate VS Code integrated
terminal tabs; neither script opens an external command window itself.

VS Code has equivalent tasks under **Terminal > Run Task**, prefixed
"KATS: Native". Those tasks always run inside the VS Code terminal.

## Local addresses

| Component | URL / endpoint |
| --- | --- |
| React UI | http://localhost:5173 |
| Flask API | http://localhost:8000 |
| Health check | http://localhost:8000/healthz |
| Database readiness | http://localhost:8000/readyz |
| Native PostgreSQL | 127.0.0.1:55432 |
| Native Redis | 127.0.0.1:56379 |

The Vite API proxy explicitly targets Flask at 127.0.0.1:8000 to avoid
Windows localhost IPv4/IPv6 DNS mismatch errors. Native database
credentials live exclusively in ignored .env.native and are not the same
credentials used by the normal Docker Compose application.

## Creating the first owner

Run this in a separate VS Code terminal after initialization:

~~~powershell
.\create-owner.bat
~~~

The backend prompts for email, display name and password interactively.
Use a fresh 12+ character password; never paste secrets in GitHub issues
or public terminal screenshots.

## Shutdown and restarting

Press Ctrl+C in the start.bat terminal to stop Vite, Flask and Celery.
Then run stop.bat (or .\stop.bat from PowerShell) to stop only the native
PostgreSQL and Redis containers.

Both database and Redis persistent volumes remain intact. On the next
startup, Alembic upgrades are idempotent and permissions are seeded only
for new routes. Never delete the database volume just to resolve a test
failure. stop.bat does not forcibly terminate an unrelated standalone
frontend or backend process; stop those with Ctrl+C in their terminals.

## Troubleshooting

- Ports 5173 or 8000 already in use: stop the standard Docker app or the
  other Vite/Flask process before launching the native stack.
- Ports 55432 or 56379 in use: another local program is occupying the
  dedicated native dependency port.
- Docker Desktop is not running: start its engine and retry.
- Python not detected: install Python 3.12+ and reopen the terminal.
- Existing .venv incompatible with Python 3.12+: close all local Python
  processes, rename the broken local venv, and run start-backend.bat again.
- npm missing or build fails: install Node 22+ and inspect the actual
  ESLint/tests/build failure before attempting to start the frontend.
- Celery worker problems on Windows: the full launcher uses --pool=solo.
  Test worker schedules and background jobs before claiming operational
  acceptance. Celery still requires real-device and environment validation.
- Backend fails its migration or readiness check: inspect the SQL error
  and preserve the local database. Do not apply destructive migration
  commands to business data.

## Security and production boundaries

This is a **local developer runtime**, never production. The application
forces external MTN MoMo, Airtel, EFRIS, SMS, email and private S3 connectors
off in native launch mode. The database is localhost-only, isolated and
persistent. The script deliberately does not reuse the standard .env.

For independent regression tests and six-role synthetic browser checks,
follow [VS Code testing](LOCAL_VSCODE_TESTING.md). For real release
approval, follow [Go-live checklist](GO_LIVE_CHECKLIST.md).
