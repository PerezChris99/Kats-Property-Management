# KATS Property Management

**© 2026 Kats Properties. All rights reserved. Proprietary software — NOT open source.**

> Unauthorized copying, distribution, hosting, resale, or reuse is prohibited without written permission from Kats Properties. Available legal remedies, including claims for damages, depend on applicable law; this notice does not create automatic charges. See [LICENSE](LICENSE) and [NOTICE](NOTICE.md).

**A unified platform for rental properties, tenants, verified collections, maintenance, and financial oversight in Uganda.**

KATS is a mobile-first management application for **one property-management business** (not a multi-tenant SaaS platform). It brings everyday rental operations into one accountable workspace. Monetary amounts are represented as whole **Ugandan shillings (UGX)**.

> [!IMPORTANT]
> **Release status: implementation is not production acceptance.** Automated backend, frontend, and PostgreSQL checks exist. MTN/Airtel money settlement, URA EFRIS fiscal documents, production storage, email/SMS providers, HostWares deployment, legal approval, and customer/device testing still need independent validation. Successful CI does not authorize processing live money.

[Architecture](docs/ARCHITECTURE.md) · [React JSX guide](docs/FRONTEND_JSX.md) · [Production security](docs/PRODUCTION_SECURITY.md) · [Delivery status](docs/DELIVERY_STATUS.md) · [Operations](docs/OPERATIONS.md) · [Production deployment](docs/PRODUCTION_DEPLOYMENT.md) · [Uganda implementation register](docs/UGANDA_AUTOPILOT_REGISTER.md) · [Go-live checklist](docs/GO_LIVE_CHECKLIST.md)

---

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

## Native Windows launcher — CMD and PowerShell

From the repository root, use **start.bat** in CMD or **.\start.bat** in PowerShell.
This builds React first, prepares the root Python .venv, installs backend dependencies,
runs Flask migrations, then starts Vite, Flask, Celery worker and scheduler in the
**same VS Code integrated terminal**. Docker Desktop supplies only a separate
localhost PostgreSQL/Redis dependency pair; no external terminal windows.

Individual files: **start-frontend.bat**, **start-backend.bat**,
**create-owner.bat**, **stop.bat**. See the
[Windows batch launcher guide](docs/WINDOWS_BATCH_LAUNCHERS.md).

**Do not run the standard Docker application and native launcher together:**
both would claim ports 5173 and 8000. Native mode never uses the operational
database; it generates ignored .env.native credentials and stores development
records in a dedicated kats_native PostgreSQL volume. Live providers are disabled.
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
