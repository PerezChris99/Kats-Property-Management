# KATS Property Management

**© 2026 Kats Properties. All rights reserved. Proprietary software — NOT open source.**

> Unauthorized copying, distribution, hosting, resale, or reuse is prohibited without written permission from Kats Properties. Available legal remedies, including claims for damages, depend on applicable law; this notice does not create automatic charges. See [LICENSE](LICENSE) and [NOTICE](NOTICE.md).

**KATS Property Management belongs exclusively to Kats Properties.** This proprietary application supports Kats Properties' rental operations in Uganda, including tenants, verified collections, maintenance, and financial oversight.

KATS is a mobile-first property management application **owned by Kats Properties** and designed for its own business (not a multi-tenant SaaS platform). It brings everyday rental operations into one accountable workspace. Monetary amounts are represented as whole **Ugandan shillings (UGX)**.

> [!IMPORTANT]
> **Release status: implementation is not production acceptance.** Automated backend, frontend, and PostgreSQL checks exist. MTN/Airtel money settlement, URA EFRIS fiscal documents, production storage, email/SMS providers, HostWares deployment, legal approval, and customer/device testing still need independent validation. Successful CI does not authorize processing live money.

**Automated testing on Windows:** Test scripts live in [`tests/`](tests/README.md), not the repository root. Run `tests\test-all.bat` in CMD or `.\tests\test-all.bat` in PowerShell from the repository root. All 16 category launchers also live in `tests/`. See [Windows testing instructions](docs/WINDOWS_TEST_LAUNCHERS.md) · [Native startup, API bridge, live logs and shutdown](docs/NATIVE_DEVELOPMENT.md). External staging load is approval-gated.

[Production PostgreSQL, RLS and performance](docs/PRODUCTION_PERFORMANCE.md) · [Architecture](docs/ARCHITECTURE.md) · [React JSX guide](docs/FRONTEND_JSX.md) · [Production security](docs/PRODUCTION_SECURITY.md) · [Delivery status](docs/DELIVERY_STATUS.md) · [Operations](docs/OPERATIONS.md) · [Production deployment](docs/PRODUCTION_DEPLOYMENT.md) · [Uganda implementation register](docs/UGANDA_AUTOPILOT_REGISTER.md) · [Go-live checklist](docs/GO_LIVE_CHECKLIST.md)

---

## Vercel + Neon demonstration

The optional Flask/Vite Vercel Services configuration, publicly labelled synthetic sample-login sidebar and guarded Neon dataset seeder are documented in [Vercel + Neon deployment](docs/VERCEL_NEON_DEPLOYMENT.md). **Not live:** the connected Vercel account returned 403 on `katsproperty` project creation. Neon has been provisioned but not migrated or seeded; Redis/workers still require an approved production setup. Never expose real tenant credentials in a public demo.

## Windows / VS Code: fast daily development

After the PostgreSQL demo was seeded once, select
**Terminal → Run Task → KATS: Start Dev (Frontend + Backend)**.

Both integrated terminal panes appear **immediately**: Flask in the left pane,
React/Vite in the right. React waits inside its visible pane for Flask SQL
readiness before opening port 5173. No daily npm build, database migrations,
permission seed, demo seed or password changes occur. All existing
`kats_demo` property, tenant and payment data is preserved.

For a **brand-new checkout only**, run the separate task
**KATS: Setup demo once + Start Dev**. It creates the isolated localhost
PostgreSQL `kats_demo`, seeds **1 OWNER + 30 TENANT** fictional logins
exactly once and then opens both service terminals. First setup may request
the PostgreSQL administrator password. SQLite is only an explicit/first-run
fallback, never silently substituted for an established PostgreSQL database.

App: http://127.0.0.1:5173 · Flask: http://127.0.0.1:8000.
Stop using `./stop.bat` or the VS Code Stop task (database preserved).
See [Windows native developer guide](docs/NATIVE_DEVELOPMENT.md).

## Compact authenticated workspaces and live analytics

Landlord and tenant dashboards share a 14px design-token system, responsive
12-column layouts and lazily loaded **Recharts** charts. The authenticated
Flask analytics endpoints aggregate PostgreSQL data,
including occupancy, collection trends, exact tenant-overlap counts, property
scores, and tenant-only payment/balance histories. Every chart has loading,
empty, error and retry states. Functional render-error boundaries and a
visible 404 avoid silent blank routes. The existing annual trends page
shares the same chart renderer. Read the
[workspace analytics and SQL documentation](docs/WORKSPACE_UI_ANALYTICS.md).

## Local PostgreSQL demo (Docker-free)

Use an existing **localhost PostgreSQL 16/17+** installation and run
`.\\ops\\local_pg_demo.bat setup` once, or select
**KATS: PostgreSQL demo setup (31 accounts)** in VS Code.
This provisions only a separate `kats_demo` database, applies real
PostgreSQL migrations/RLS, seeds 1 landlord and 30 tenants, and verifies
database rows and authenticated API sessions. Start with
**KATS: PostgreSQL demo start (31 accounts)** and use the usual login page.
No Docker is needed for this demo, although the complete isolated test suite
continues to require Docker. See [Local PostgreSQL demo](docs/LOCAL_POSTGRES_DEMO.md).

## One-click local landlord and tenant demo

From VS Code, run **KATS: Demo start (landlord + 30 tenants)**, then open `http://127.0.0.1:5173/login`. Click the landlord entry or any of 30 searchable synthetic tenant accounts to sign in instantly. The local-only preview seeds linked properties, leases, invoices and sample payments; production auth is unchanged. See [Demo preview instructions](docs/DEMO_PREVIEW.md).

## Dedicated development ports

React/Vite defaults to **`127.0.0.1:5173`**, Flask to **`127.0.0.1:8000`**.
[`ops/dev_ports.json`](ops/dev_ports.json) is their shared source of truth.
Each process binds independently on loopback; Vite has strict port binding
and forwards API/health requests to Flask. A collision is reported, not
silently reassigned. Production reverse-proxy ports are separate.

## Parallel VS Code development

Select **Tasks: Run Task → KATS: Start Dev (Frontend + Backend)**.
Two independent integrated terminals start **in parallel**: Flask/backend
**left** and React/Vite frontend **right**. Logs stream live in both.
Regular starts never run a release build, npm/pip install or migrations.
Run **KATS: Native setup (database + build)** once for missing prerequisites.

Alternatively run ` .\start.bat ` from PowerShell to open the exact
backend-left/frontend-right layout in Windows Terminal. Access the UI at
**http://127.0.0.1:5173**, with Flask on port 8000.
See [native runbook](docs/NATIVE_DEVELOPMENT.md) for details.

## 1. Core capabilities

| Area | Implemented |
| --- | --- |
| **Portfolio** | Properties, buildings, floors, room placement, status history, portfolio editing, caretaker assignments |
| **Tenants & leases** | Tenant records, one-use account invitations, leases, dated renewals, inspections, move-out controls |
| **Rent & invoicing** | Monthly billing, invoice line items, calendar-day proration with approval, credits, balances, arrears |
| **Payments** | Cash/bank verification by a second person, MTN/Airtel adapter boundaries, idempotent provider status checks, accounting reversals |
| **Deposits & expenses** | Deposit hold/withhold/refund records, independent approvals, expense review, immutable accounting events |
| **Operations** | Maintenance requests, work orders, caretakers, reminders, inquiries, private-document integration |
| **Reporting** | Occupancy, aging, monthly financial trends, tenant statements, internal receipts, CSV/XLSX exports |
| **Administration** | Role-scoped portals, permission controls, secure sessions, audit records, versioned legal pages |

**Boundaries:** Payment initiation is not successful settlement; an accounting refund record is not a bank transfer; an internal receipt is not a URA tax document. Financial trend metrics are not a certified cash-flow or profit-and-loss statement.

## 2. Architecture

### Runtime topology

~~~mermaid
flowchart TB
    subgraph Client["Client"]
      UI["React + JavaScript / JSX<br/>Responsive PWA"]
      ROLES["Owner · Manager · Accountant<br/>Caretaker · Tenant"]
    end
    subgraph Application["Application runtime"]
      NGINX["Nginx<br/>Frontend + API proxy"]
      API["Flask / Gunicorn<br/>Domain APIs and auth"]
      BEAT["Celery Beat<br/>Schedules"]
      WORKER["Celery worker<br/>Async / retry jobs"]
    end
    subgraph Stores["State"]
      PG[("PostgreSQL 16<br/>SQLAlchemy / Alembic")]
      REDIS[("Redis<br/>Task broker")]
    end
    subgraph Providers["External — activation pending"]
      MONEY["MTN MoMo / Airtel Money"]
      EFRIS["URA-approved EFRIS adapter"]
      DOCS["Private S3-compatible storage"]
      MAIL["Transactional TLS email / messaging"]
    end
    ROLES --> UI --> NGINX --> API
    API --> PG
    API --> REDIS
    BEAT --> REDIS --> WORKER --> PG
    API -. "Approved configuration" .-> MONEY
    WORKER -. "Fiscal outbox" .-> EFRIS
    API -. "Signed URLs" .-> DOCS
    API -. "TLS sender" .-> MAIL
~~~

**Key decisions**

- Single-business property management; properties represent locations, not SaaS customer tenants.
- Server-side role ceilings, database permission grants, and object-level tenant/caretaker scope.
- Immutable history for financial and audit-sensitive records; corrections use explicit reversal events.
- Idempotent collection commands and atomic database posting after external verification.
- Worker queues for recurring billing, reminders, and bounded provider retries.
- Third-party money and fiscal services remain disabled until required approvals and tests.

### Repository structure

~~~text
Kats-Property-Management/
├── backend/
│   ├── app/                   Flask APIs, auth, finance, jobs, integrations
│   ├── migrations/            Alembic versioned database schema
│   ├── tests/                 API, security, finance, PostgreSQL checks
│   └── Dockerfile
├── frontend/
│   ├── src/                   React portals, reusable navigation, styles
│   ├── public/                PWA manifest and offline fallback
│   └── nginx.conf
├── docs/                      Architecture, runbooks, acceptance status
├── ops/                       Encrypted backup, restore, smoke checks
├── .github/workflows/         Automated verification
├── docker-compose.yml         Local-only development stack
└── .env.example               Non-secret configuration template
~~~

## 3. Business workflows

### Property and tenant onboarding

~~~mermaid
flowchart TD
    P["Create property"] --> B["Add buildings and floors"]
    B --> R["Register rooms and UGX asking rates"]
    R --> T["Onboard tenant"]
    T --> I["Owner issues one-time invitation"]
    I --> A{"Email link accepted?"}
    A -- "No" --> WAIT["Account remains inactive"]
    WAIT --> I
    A -- "Yes" --> PASSWORD["User sets password"]
    PASSWORD --> LEASE["Record lease with agreed terms"]
    LEASE --> PORTAL["Scoped tenant portal"]
~~~

Invitations expire after 48 hours and password-reset links after 30 minutes. Email delivery requires authenticated TLS SMTP. Tenant identity and signed lease documentation must be verified operationally.

### Rent billing and proration

~~~mermaid
flowchart TD
    LEASE["Active lease with dated rent terms"] --> MONTH{"Full billing month?"}
    MONTH -- "Yes" --> AUTO["Idempotent monthly rent invoice"]
    MONTH -- "No / rate change" --> PREVIEW["Manual calendar-day preview"]
    PREVIEW --> APPROVE{"Finance verifies lease<br/>and approves policy?"}
    APPROVE -- "No" --> WAIT["Invoice not issued"]
    APPROVE -- "Yes" --> ISSUE["Issue reviewed invoice"]
    AUTO --> LINES["Invoice lines and ledger event"]
    ISSUE --> LINES
    LINES --> CREDIT["Optional credit note"]
    CREDIT --> BALANCE["Open amount = billed - credits - verified payments"]
~~~

Partial-month rent is never silently charged using an unapproved formula. Calendar-day proration requires explicit authorized confirmation.

### Payment intake and reconciliation

~~~mermaid
flowchart TD
    INV["Issued invoice"] --> METHOD{"Collection method"}
    METHOD -- "Cash / bank" --> PENDING["Pending payment claim"]
    PENDING --> MAKER{"Another authorized reviewer<br/>confirms evidence?"}
    MAKER -- "No" --> HOLD["No invoice credit"]
    METHOD -- "MTN / Airtel" --> REQUEST["Provider payment request"]
    REQUEST --> VERIFY{"Independent verified<br/>status, amount, currency and reference?"}
    VERIFY -- "No / unclear" --> HOLD
    VERIFY -- "Yes" --> POST["Single atomic database posting"]
    MAKER -- "Yes" --> POST
    POST --> LEDGER["Reconciled payment, invoice credit<br/>and immutable ledger event"]
    LEDGER --> REVERSE["Corrections use audited reversals<br/>not automatic cash refunds"]
~~~

Provider onboarding and real sandbox reconciliation are pending. This architecture intentionally fails closed when external settlement cannot be verified.

### Maintenance, inspections, and deposits

~~~mermaid
flowchart LR
    ISSUE["Tenant / caretaker issue"] --> WORK["Maintenance work order"]
    WORK --> CHECK["Inspection / damage evidence"]
    CHECK --> EXIT["Controlled move-out"]
    EXIT --> HOLD["Deposit movement record"]
    HOLD --> REVIEW["Independent approval"]
    REVIEW --> BANK["Bank / provider payout and<br/>real evidence — external gate"]
~~~

### EFRIS fiscalization

~~~mermaid
flowchart TD
    I["Eligible invoice"] --> Q["Durable fiscal outbox"]
    Q --> GATE{"Approved URA taxpayer connector installed?"}
    GATE -- "No" --> PENDING["Not fiscalized"]
    GATE -- "Yes" --> URA["Authenticated URA submission"]
    URA --> RESULT{"Authenticated result and valid fiscal proof?"}
    RESULT -- "Retryable" --> RETRY["Bounded retry"]
    RETRY --> URA
    RESULT -- "Rejected" --> REJECT["Record rejection"]
    RESULT -- "Accepted" --> ACCEPT["Record URA fiscal number,<br/>QR and verification link"]
~~~

Internal payment receipts remain explicitly **non-fiscal**. Actual EFRIS activation requires a taxpayer-specific approved adapter and URA acceptance.

## 4. Roles and access model

| Role | Primary responsibilities |
| --- | --- |
| Owner | Portfolio oversight, invitations, financial approvals, policy and audit visibility |
| Super administrator | Elevated system administration and permission-grant management |
| Manager | Property, tenant, lease, room, inspection, and maintenance operations |
| Accountant | Invoice/expense reviews, collections, credits, reports, fiscal queue visibility |
| Caretaker | Only assigned rooms, work orders, limited cash collection and inspections |
| Tenant | Own lease, invoices, payments, internal receipts, and maintenance requests |

The frontend menu does **not** grant authorization. The backend enforces role ceilings, explicit database grants, and record-level access. New protected routes must be seeded after migrations; existing grants are not overwritten.

## 5. Technology

| Layer | Technology |
| --- | --- |
| UI | React 19, JavaScript / JSX, Vite, React Router, Lucide, responsive CSS, PWA |
| API | Python 3.12+, Flask, Gunicorn, Argon2id, cookie-based JWT, CSRF |
| Database | PostgreSQL 16, SQLAlchemy, Alembic |
| Tasks | Redis, Celery workers, Celery Beat |
| Runtime | Docker Compose, Nginx |
| External contracts | MTN MoMo, Airtel Money, EFRIS, S3-compatible storage, TLS SMTP |

**Design language:** midnight navy, sky blue, whitesmoke, carefully restrained warm yellow; legible type, clean data hierarchy, mobile navigation, keyboard search, short transitions, and reduced-motion support.

## Native Windows startup — frontend and backend side by side

**Within VS Code:** Press **Ctrl+Shift+P**, run **Tasks: Run Task**, then choose **KATS: Start Dev (Frontend + Backend)** (also available as **KATS: Native start (split in VS Code)**). VS Code opens two **side-by-side integrated terminal panes**: React on the left and Flask + Celery worker + Celery beat on the right. The two tasks run independently and preserve their logs.

**Paths containing spaces:** VS Code's native launch and test tasks use argument-safe process execution, so `D:\NEW PROJECTS\Kats-Property-Management` works without the previous PowerShell/`cmd.exe /c` quoting error.

**From CMD or PowerShell:** Run `start.bat` or `.\start.bat` respectively. The script automatically opens **one Windows Terminal window with two side-by-side panes**. Direct batch files cannot create VS Code integrated terminal panes; for those use the VS Code task. `wt.exe` (Windows Terminal) is needed only for direct invocation.

React builds successfully before its Vite dev server starts. The backend creates/reuses `.venv` and installs Python requirements. **With Docker installed**, it provisions isolated PostgreSQL/Redis, runs migrations, seeds permissions, then launches Flask and Celery worker/Beat. **Without Docker**, the backend automatically starts an isolated, persistent **SQLite preview** (no Redis or Celery worker/Beat), initializing its tables and role permissions. This preview is for local UI/API exploration only; PostgreSQL/RLS, background scheduling, payment settlement, and release-readiness tests still require full dependencies. Both panes share atomically initialized `.env.native` development credentials; SQLite preview data stays in ignored `.local/kats-preview.sqlite3`. Ctrl+C stops the service(s) in that pane. Database volumes are retained.

Individual launch commands `start-frontend.bat`, `start-backend.bat` (Flask only), `create-owner.bat` and `stop.bat` are still supported. Full instructions: [Windows startup guide](docs/WINDOWS_BATCH_LAUNCHERS.md).

**Do not start the separate Docker application simultaneously:** both environments may claim ports 5173 and 8000. Live payment/tax/SMS connectors remain disabled in native development mode.

## Property-first public website (November 2026)

The KATS public entry is deliberately minimal: **Home, Features, How It Works, About, Request Access**. Account access and legal routes remain available. The operational product is the authenticated, role-scoped property-management system—not the public entry pages.

The hero now uses **five verified Ugandan property photographs** licensed
CC BY-SA 4.0, with compact glass text, a smooth GPU parallax layer,
carousel controls and reduced-motion support. Cards and forms use fluid,
screen-bounded grids. Sources and reuse terms are recorded in
[IMAGE_SOURCES.md](docs/IMAGE_SOURCES.md) and credited in the public footer.
Photos are illustrative, not KATS customer or partner endorsements.
An original SVG KATS mark is included at frontend/public/brand-mark.svg.

The About charts are explicitly illustrative and never claim customer
performance or actual operational values. Real account metrics remain
protected within role-based workspaces. Feature descriptions distinguish
shipped workflows from optional provider integrations.

The Request Access page posts to /api/v1/public/access-requests, requires consent, and queues the application for owner review. It **does not create an account**. The legacy contact API is retained for backwards compatibility.
Sign In retains the real authentication and optional MFA flow; unimplemented
social sign-in is not advertised. Existing portal routes remain intact.

Legal pages are informational drafts until a property operator approves and
publishes specific versions in the Legal admin workspace. The public site
prioritizes published text over drafts. Review is required for local law,
privacy controller identity, retention schedules, hosting and support terms.
## 6. Quick start

### Prerequisites

Docker Desktop (Windows) or Docker Engine with Compose, Git, and a terminal. Node.js 22+ and Python 3.12+ are required for native development outside Docker.

~~~bash
git clone https://github.com/PerezChris99/Kats-Property-Management.git
cd Kats-Property-Management
cp .env.example .env
~~~

On Windows PowerShell, copy the template with:

~~~powershell
Copy-Item .env.example .env
~~~

Edit the resulting **.env**: replace the example PostgreSQL password and choose **different, unpredictable 32+-character secrets** for SECRET_KEY and JWT_SECRET_KEY. Keep MTN_MOMO_ENABLED, AIRTEL_MONEY_ENABLED, and EFRIS_ENABLED set to false until real provider acceptance.

### Start services and bootstrap the owner

~~~bash
docker compose up --build -d
docker compose exec api flask --app wsgi db upgrade
docker compose exec api flask --app wsgi seed-permissions
docker compose exec api flask --app wsgi create-user --role OWNER
~~~

The last command interactively prompts for the first owner's identity and password within the server console. Do not store credentials in version control or runbooks.

| Local URL | Function |
| --- | --- |
| http://localhost:5173 | Web application served from compiled frontend |
| http://localhost:8000/healthz | API health |
| http://localhost:8000/readyz | Database readiness |

**Note:** Docker Compose exposes HTTP only on localhost. It is not an internet-facing HTTPS deployment.

### Common operations

~~~bash
docker compose ps
docker compose logs -f api worker beat
docker compose exec api flask --app wsgi db upgrade
docker compose exec api flask --app wsgi seed-permissions
docker compose down
~~~

Stopping containers preserves the volumes by default. Avoid removing volumes containing needed data.

### Frontend development — JavaScript and JSX

The React frontend uses **plain JavaScript (`.js`) and JSX (`.jsx`)**, not TypeScript/TSX. Its quality gate combines ESLint, React Hooks checks, targeted JavaScript tests and a Vite production build.

~~~bash
cd frontend
npm ci
npm run dev
npm run lint
npm test
npm run build
~~~

Vite handles hot reload in development. Docker serves compiled assets and does not hot-reload Vite files. For architecture, conventions and testing see the [JSX frontend guide](docs/FRONTEND_JSX.md).

## 7. Secure external configuration

| Integration | Activation requirements |
| --- | --- |
| Transactional invitations / password reset | Approved PUBLIC_APP_URL, MAIL_FROM and SMTP_HOST, SMTP_PORT (465/587), SMTP_USERNAME, SMTP_PASSWORD; verified domain/deliverability |
| MTN MoMo | Merchant account, secrets, approved callback/status schemas, sandbox-to-ledger reconciliation |
| Airtel Money | Approved merchant profile and actual payout/collection response verification |
| URA EFRIS | Registered taxpayer, applicable fiscal obligations, approved signed/encrypted adapter, accepted fiscal-document verification |
| Private documents | S3-compatible endpoint, private bucket, signed URLs, object malware validation, retention controls |
| SMS / messaging | Approved communications provider, privacy consent, sender registration and delivery acceptance |
| HostWares | Separate staging/production environments, HTTPS, secrets, monitoring, tested offsite restore, release plan |

Never enable an external integration solely because an API key is present.

## 8. Testing and safety

**Backend tests**

~~~bash
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
~~~

**Frontend build**

~~~bash
cd frontend
npm install --no-audit --no-fund
npm run build
~~~

The [GitHub verification workflow](.github/workflows/verify.yml) checks Python tests and compilation, frontend type checking/production build, PostgreSQL 16 schema upgrade-downgrade-upgrade, and targeted PostgreSQL runtime tests (including concurrent approval and append-only audit protections).

Security and accounting invariants include:

- Monetary values in whole UGX; reviewed and idempotent posting of verified transactions.
- Separate manual-payment and expense reviewers, immutable finance/audit events, explicit reversals.
- Argon2id passwords, CSRF, refresh-token rotation, account/session invalidation, strict HTTPS production origins.
- Tenant and caretaker object scoping; auditable super-admin permission changes.
- No private API response caching by the PWA.
- Encrypted offsite backups, periodic restore rehearsal, alerts and failure drills before go-live.

Automated coverage reduces risk; it is not a guarantee of error-free, attack-proof, or tax-compliant production operation.

## 9. Delivery workflow

~~~mermaid
flowchart LR
    DEV["Develop and commit on perez"] --> CI["Build · tests · migrations"]
    CI --> OK{"All checks pass?"}
    OK -- "No" --> FIX["Fix / retest on perez"]
    FIX --> CI
    OK -- "Yes" --> PR["Review pull request"]
    PR --> MAIN["Merge into main"]
    MAIN --> ACCEPT{"External and customer acceptance?"}
    ACCEPT -- "Not yet" --> HOLD["Code merged; no production tag"]
    ACCEPT -- "Approved" --> STAGE["Stage, verify, deploy and monitor"]
~~~

Use the existing **perez → main** workflow. Do not add unnecessary branches or leave orphaned commits. A merged commit confirms code integration, not deployment.

## Production hardening and ownership

**© 2026 Kats Properties. All rights reserved.** This repository is proprietary and **not open source**. No public permission to copy, fork, distribute, host, sublicense or commercialize is granted. See [LICENSE](LICENSE) and [NOTICE](NOTICE.md). Legal remedies require applicable law and are not automatic charges.

The current security baseline and its limits are documented in the [production security/capacity checklist](docs/PRODUCTION_SECURITY.md). Implemented controls include Redis rate limits, strict CORS/CSRF and secure cookies, request size guards, non-cacheable private API data, Nginx CSP and backpressure, SQL pool limits, targeted PostgreSQL indexes, RBAC/permission grants, and FORCE RLS specifically for private documents. **Other financial/tenant tables are protected by application authorization, not a universal RLS policy.** Production acceptance still requires external penetration/load testing, the real trusted-proxy/TLS chain, least-privilege database credentials, backup-restore drills and approved integrations.

## 10. Documentation and launch gates

| Reference | Purpose |
| --- | --- |
| [Architecture](docs/ARCHITECTURE.md) | Scope, design decisions, security and data invariants |
| [Delivery status](docs/DELIVERY_STATUS.md) | Implemented modules, gaps, and dependencies |
| [Operations](docs/OPERATIONS.md) | Reconciliation, recovery, ongoing support |
| [HostWares deployment](docs/HOSTWARES_DEPLOYMENT.md) | Staging/production checklist and failure recovery |
| [Go-live checklist](docs/GO_LIVE_CHECKLIST.md) | Evidence-based acceptance before launch |

**Security and efficiency baseline:** API requests are rate-limited through Redis in production; PostgreSQL uses bounded pools, query timeouts, targeted indexes, and limited pagination. Private documents additionally enforce PostgreSQL row-level security. Run `flask --app wsgi security-preflight` using the **restricted production application database role** after migrations. For benchmarks, an explicitly approved HTTPS staging target can be tested with `KATS_LOAD_TEST_APPROVED=yes BASE_URL=https://<staging-host> k6 run ops/load-test.js`. Never run load tests against live payment providers or unapproved production hosts. Full configuration and limitations are described in [Production security](docs/PRODUCTION_SECURITY.md).

**Still outstanding:** actual MTN/Airtel merchant and URA approvals, provider-specific fiscal credit/refund behavior, real bank disbursement, email/SMS delivery activation, private storage and malware scanning, signed document and advanced operational workflows, deployment/TLS, backups and restore drills, penetration/load tests, legal review, and real-device UAT. Consult the delivery register; do not relabel all remaining work as infrastructure-only.

---

**KATS Property Management** · Owned exclusively by **Kats Properties**. © 2026 Kats Properties. All rights reserved.


### 2026-11-10 rental operations and security upgrade

The app now provides tenant-visible rental disputes and repeatable preventive maintenance plans, alongside configurable room water/electricity meter records with
independently approved invoice charges, Uganda default rent-increase notice
records, protection against overlapping rent invoices, zero-to-one-month
security deposit safeguards, improved tenant balances, printable in-person
cash custody acknowledgements, opt-in encrypted TOTP MFA, personal-data
request review, and security-scanned, version-pinned private document
downloads (only with approved S3/ClamAV infrastructure). Production Compose
and a Caddy TLS edge are packaged but **not deployed**.

See [Uganda implementation/remaining-work register](docs/UGANDA_AUTOPILOT_REGISTER.md).
No live payment provider or URA EFRIS connection is represented as verified.

## Local VS Code development and test acceptance

Use the [VS Code local test and acceptance guide](docs/LOCAL_VSCODE_TESTING.md) for one-command Docker startup, isolated PostgreSQL integration tests, disposable six-role browser E2E, safe owner bootstrap and detailed role-based test instructions. In a VS Code PowerShell terminal: ` .\ops\dev.ps1 -Action all `. This does **not** certify live-provider or business go-live acceptance.

## Single-owner property management modernization

KATS is a private **one-owner system**, not SaaS. One owner and their authorized
staff manage properties across Uganda, with separate tenant/caretaker access.
There is **no subscriber onboarding, subscription pricing, independent customer
organization management or SaaS tier enforcement**. Historic organization
registry tables remain dormant solely to preserve database migration compatibility.
See [docs/NATIONWIDE_MODERNIZATION.md](docs/NATIONWIDE_MODERNIZATION.md)
for the owner-focused implementation and verification register.
Live financial providers, banking, fiscal integrations, production restoration,
legal review and physical device acceptance remain release gates.
