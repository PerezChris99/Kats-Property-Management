# KATS — Windows test commands (CMD and PowerShell)

These scripts are designed for the **VS Code integrated terminal**. They run
in the current CMD or PowerShell terminal, do not open external console windows,
and return a **nonzero exit code** when a test fails.

## Prerequisites

Windows 10/11, Python 3.12+, Node.js 22+, npm, Git and Docker Desktop
(Linux containers) are required for the full test suite. First-time runs need
internet access to install packages and Playwright Chromium. The external
staging load test additionally needs k6.

## Run every available LOCAL automated test

CMD:
~~~cmd
test-all.bat
~~~

PowerShell:
~~~powershell
.\test-all.bat
~~~

The full suite performs all these checks and gives an overall pass/fail
summary: repository secret scanning, Python syntax and Compose configuration,
React JSX verification/ESLint/Node tests/production build, **every backend
pytest test with coverage**, isolated PostgreSQL 16 migration
upgrade–downgrade–upgrade plus concurrent financial invariant and document
RLS tests, and Chromium testing with all six synthetic user roles.

The browser suite tests public/API smoke, responsive widths, anonymous
route restrictions and authenticated navigation. It runs against disposable
localhost:5174 containers, never business credentials or production data.
The PostgreSQL tests run in an independent database named kats_ci with tmpfs
storage and **no public port**, entirely separate from the regular Kats
application database.

## Individual test categories

In **CMD**, use the filename shown. In **PowerShell**, put .\ before it.
Every category can run independently:

| Category | Batch file | Scope |
| --- | --- | --- |
| Full automated suite | test-all.bat | All local automated tests including backend coverage |
| Frontend full | test-frontend.bat | JSX, lint, JavaScript tests and Vite production build |
| Frontend unit | test-frontend-unit.bat | All Node test files |
| JSX and lint | test-lint.bat | JSX-only enforcement and ESLint |
| Frontend build | test-build.bat | React build (includes its checks and unit tests) |
| Backend full | test-backend.bat | Entire Python pytest suite |
| API tests | test-api.bat | Authorization, sessions, permissions and workflow contracts |
| Security | test-security.bat | Secret scan, abuse controls, MFA, authorization, account recovery |
| PostgreSQL | test-database.bat | Migration roundtrip, immutable ledger, concurrency, restricted-role RLS |
| Migrations | test-migrations.bat | PostgreSQL upgrade/downgrade/upgrade alone |
| Performance regression | test-performance.bat | Batched rent and maintenance query-count budgets |
| Browser / E2E | test-e2e.bat | Six test roles, public/browser/API smoke and responsive checks |
| Live local smoke | test-smoke.bat | HTTP GET checks against an already running localhost app |
| Static configuration | test-config.bat | Secrets, Python compilation, VS Code JSON, all Compose manifests |
| Backend coverage | test-coverage.bat | Full pytest suite, detailed coverage and XML report |
| External load (opt-in) | test-load.bat | k6 p95/p99/error thresholds on approved HTTPS staging |

Coverage XML is generated locally at .local/coverage.xml, excluded from Git.
The all-tests script uses the coverage category to run the entire backend
pytest suite, so running the separate backend, API, security or performance
batches again afterward is optional and duplicates some checks.

## Local smoke requires a running system

First start the local app with start.bat or with the existing Docker stack.
Then run test-smoke.bat. It tests local UI, health, database readiness,
public landing API and rejection of unauthenticated private API requests.
Allowed hosts are only localhost and 127.0.0.1, ports 5173 or 5174.
Unlike the full E2E test, the standalone smoke script does not start a server.

## External staging load test (NOT part of the all-tests script)

Load testing is deliberately excluded from automatic full-suite runs. It
requires an approved HTTPS staging environment, k6 installed, and explicit
authorization. Never direct it at production tenant data, payment gateways or
a third-party service without permission.

PowerShell:
~~~powershell
$env:KATS_LOAD_TEST_APPROVED = 'yes'
$env:BASE_URL = 'https://your-approved-staging-host.example'
.\test-load.bat
Remove-Item Env:KATS_LOAD_TEST_APPROVED,Env:BASE_URL -ErrorAction SilentlyContinue
~~~

CMD:
~~~cmd
set KATS_LOAD_TEST_APPROVED=yes
set BASE_URL=https://your-approved-staging-host.example
test-load.bat
set KATS_LOAD_TEST_APPROVED=
set BASE_URL=
~~~

Missing authorization causes test-load.bat to fail without making requests.

## VS Code tasks

Open **Terminal > Run Task** and choose a task prefixed with
**KATS Test:**. Each category has its own entry, including the full suite.

## Important limitations

Test-all.bat runs every existing locally automatable test type. This does
**not** prove every possible real-world workflow was exercised. Real-device
UAT, third-party provider acceptance, approved load/penetration testing,
backup restore drills, bank settlements, legal review and remaining application
development must still be completed or independently accepted before go-live.

For starting the application, use [Windows batch launchers](WINDOWS_BATCH_LAUNCHERS.md).
For detailed human acceptance, see [VS Code testing](LOCAL_VSCODE_TESTING.md)
and the [go-live checklist](GO_LIVE_CHECKLIST.md).
