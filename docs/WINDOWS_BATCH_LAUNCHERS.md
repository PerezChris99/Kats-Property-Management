# KATS — Windows startup with side-by-side frontend and backend

## Choose your terminal host

### VS Code: two integrated panes (recommended)

Open the repository folder in VS Code. Press **Ctrl+Shift+P**, select **Tasks: Run Task**, then select **KATS: Start Dev (Frontend + Backend)**. Alternatively use **Terminal → Run Task** or the existing **KATS: Native start (split in VS Code)** entry.

All KATS Windows VS Code tasks now use argument-safe **process tasks**, not a
nested PowerShell → `cmd.exe /c` string. This fixes the previous
`'D:\\NEW' is not recognized` error for checkouts under paths with spaces
such as `D:\\NEW PROJECTS\\Kats-Property-Management`. The shared
`ops/vscode_task.ps1` dispatcher invokes the correct batch script, stays
inside VS Code and returns its exit code. The same fix applies to all 16
`tests/` batch tasks and owner/start/stop tasks.

The compound VS Code task runs the frontend and backend in parallel using the same terminal presentation group. VS Code displays **two terminal panes side by side in its own terminal panel**, with separate output, tasks and Ctrl+C handling. No external window is launched. This relies on VS Code's built-in task API, not an extension.

### Direct start.bat: two Windows Terminal panes

From the repository root in CMD:

~~~cmd
start.bat
~~~

From PowerShell:

~~~powershell
.\start.bat
~~~

This opens a **new Windows Terminal window** (`wt.exe`) with a vertical split: **left pane React**, **right pane Flask + Celery worker + Celery beat**. The launcher immediately returns to the original shell after dispatch. The two panes each retain their own logs and processes. If you want the panes **inside VS Code**, use the VS Code task above instead: a standalone batch process cannot instruct VS Code's UI to split its integrated terminal without VS Code's task/extension APIs.

Windows Terminal is included on many Windows 11 systems; if `wt.exe` is unavailable, install it or use the VS Code task. Do not substitute two floating Command Prompt windows.

## Prerequisites

Windows 10/11, Python 3.12+, Node.js 22+ with npm, and Git. **Docker Desktop is optional for local preview**, but required for full PostgreSQL/Redis + Celery integration and production-like acceptance tests. Use VS Code to get integrated split panes, or Windows Terminal to start from a standalone batch file. Internet access is needed to install the project's dependencies on the first run.

## What runs in each pane

| Left — frontend | Right — backend |
| --- | --- |
| `start-frontend.bat` | `ops\launch.bat backend-stack` |
| Install locked npm dependencies if needed | Create/reuse `.venv`, install backend Python dependencies |
| Validate JSX-only source, run ESLint, Node tests and Vite build | Start isolated native PostgreSQL and Redis containers |
| Start Vite development server on localhost:5173 | Apply Alembic migrations, seed permissions |
| Show React/Vite logs and exit status | Run Flask on localhost:8000, plus Celery solo worker and Beat **only in Docker-backed mode** |

The panes start **concurrently**, rather than serially: the frontend may become ready before the backend finishes migrating. They share a safely and atomically generated, gitignored `.env.native`, and **never** use the main application's operational PostgreSQL data. In SQLite preview, the local DB uses the ignored `.local/` directory. The backend ensures the Celery schedule directory exists before launch. Both panes check for port conflicts; avoid running the existing Docker-based application simultaneously.

Each pane can be stopped independently with Ctrl+C. The backend pane stops its Flask, Celery worker and Celery Beat process tree. Stop both panes before running `stop.bat` to stop Docker dependencies. Local database volumes are preserved.

## Docker-free development preview (automatic)

When Docker is **not installed**, the backend automatically switches to an **isolated SQLite preview** rather than failing at `Missing docker`. No PostgreSQL, Redis, WSL, third-party services or external account is required to explore the React UI and Flask API.

- SQLite file: `.local/kats-preview.sqlite3` (gitignored, local-only, preserved between restarts)
- Rate limiter: in-memory (single developer process only)
- Celery: synchronous in-process preview tasks; **no Celery worker or Celery Beat**. Scheduled notifications, billing and background processing are **not** running automatically
- Database initialization: `db.create_all()` creates preview tables and seeds route permissions; **no Alembic upgrade, PostgreSQL RLS, triggers or production schema guarantees**
- Live money/tax/SMS/email/storage integrations remain disabled; **never enter actual customer or payment data**
- The `create-owner.bat` command uses the same preview database and can bootstrap an OWNER account for testing
- `stop.bat` has nothing to stop if Docker is absent; the preview DB remains preserved

To force SQLite preview even when Docker is installed, in PowerShell run:

~~~powershell
$env:KATS_DEV_BACKEND = 'preview'
# Ctrl+Shift+P → Tasks: Run Task → KATS: Start Dev (Frontend + Backend)
~~~

To require full Docker-backed PostgreSQL/Redis and disable fallback:

~~~powershell
$env:KATS_DEV_BACKEND = 'docker'
# Start Docker Desktop, then run the dev task again
~~~

The default is `auto`: Docker executable detected → Docker-backed mode; not installed → SQLite preview. If Docker is installed but its engine isn't running, start Docker Desktop or explicitly opt into preview. Avoid deleting `.local/kats-preview.sqlite3` without backing up any needed demo records. SQLite `create_all()` does not migrate earlier preview tables; after model schema changes, create a fresh disposable preview database if necessary.

**Preview is not equivalent to the full system.** To test financial invariants, document RLS, concurrent transactions, Celery scheduling, payments and release acceptance, install Docker and run the full integration suite. Do not treat successful preview startup as deployment or compliance readiness.
## Individual commands

| Operation | CMD | PowerShell |
| --- | --- | --- |
| Full stack (Windows Terminal split) | `start.bat` | `.\start.bat` |
| React independently | `start-frontend.bat` | `.\start-frontend.bat` |
| Flask independently (without Celery) | `start-backend.bat` | `.\start-backend.bat` |
| Create first owner interactively | `create-owner.bat` | `.\create-owner.bat` |
| Stop native PostgreSQL + Redis | `stop.bat` | `.\stop.bat` |

From **VS Code Terminal → Run Task** you can also run **KATS: Native frontend (BAT)**, **KATS: Native backend (BAT)**, or **KATS: Native backend stack (BAT)** individually.

## Local endpoints

| Service | Address |
| --- | --- |
| React UI | http://localhost:5173 |
| Flask API | http://localhost:8000 |
| Flask readiness | http://localhost:8000/readyz |
| PostgreSQL (local only) | 127.0.0.1:55432 |
| Redis (local only) | 127.0.0.1:56379 |

## Troubleshooting

- If `wt.exe` is unavailable, enable its **App Execution Alias** in Windows Settings, install Windows Terminal, or use the VS Code task for integrated panes.
- If direct `start.bat` opened a new window rather than splitting VS Code's terminal, this is expected. Use **KATS: Native start (split in VS Code)** for true integrated split panes.
- If the frontend fails, inspect the **left pane** for npm, ESLint, JSX, test or build errors.
- If Flask, migrations or Celery fail, inspect the **right pane**; it owns database setup, Flask and background workers.
- If a port is occupied (5173/8000), stop the existing local development stack first.
- If Python 3.12+/Node 22+ is missing, install it and reopen VS Code.
- If Docker Desktop is not installed, KATS automatically starts the SQLite preview. If Docker is installed but its engine is stopped, start Docker Desktop or explicitly set `KATS_DEV_BACKEND=preview`.
- If local `.venv` was created under incompatible Python, rename it and rerun the backend.
- The startup configuration is for **development only**; it disables MTN/Airtel/URA and external mail/SMS/storage integrations and is not a live-service acceptance run.

## Test scripts

All test batch scripts remain in `tests/`. From PowerShell run `.\tests\test-all.bat` for the full locally automated test suite. For details, see [Windows test commands](WINDOWS_TEST_LAUNCHERS.md).

User acceptance, real payment gateways, and production infrastructure still need separate verification. See the [go-live checklist](GO_LIVE_CHECKLIST.md).