# Kats Property Management

Mobile-first rental property-management platform for a single rental business in Uganda. All monetary amounts are stored as **integer Ugandan shillings**.

**Status: code on development/review branches is not equivalent to live launch acceptance.** MTN/Airtel collections, EFRIS fiscal documents, email/SMS providers, object storage and HostWares deployment require third-party approval and real infrastructure tests before handling money or sensitive tenant documents.

## Architecture

- Backend: Python 3.12+, Flask, SQLAlchemy 2, PostgreSQL 16 and Alembic.
- Worker: Celery/Redis for monthly invoices, rent reminders, lease expiry, provider-status polling and fiscal-outbox processing.
- Frontend: React + TypeScript + Vite, mobile-first navigation and static offline fallback PWA.
- Auth: Argon2id, HttpOnly JWT cookies, CSRF, one-time refresh-token rotation and session-version invalidation.
- Role enforcement: server-side role ceilings plus editable, audited database role grants; tenant/assigned-caretaker query scoping.
- Finance: invoice charge lines, verified payments, reversal ledger, credit notes, timed rent renewal, deposit approval and reporting.
- Integrations: server-side MTN/Airtel adapters and idempotent EFRIS outbox; all **disabled until provider acceptance**.
- Documents: private S3-compatible signed upload/download with 8 MB cap; requires object-storage credentials.
- Reports: CSV/Excel invoice exports, internal payment receipt PDFs, tenant statement PDFs and arrears aging.
- Operations: work orders, inspections, contact/demo inbox, editable versioned legal pages and audit trails.

## Local setup

1. Copy `.env.example` to `.env`, change example DB password, generate two different unpredictable 32+ character secrets and configure PostgreSQL/Redis URLs.
2. Start Docker services: `docker compose up --build -d`.
3. Apply all migrations: `docker compose exec api flask --app wsgi db upgrade`.
4. **Seed the database permission registry:** `docker compose exec api flask --app wsgi seed-permissions`. Repeat after shipping new endpoint permissions; existing permission edits are preserved.
5. Create your first owner account securely from the server console: `docker compose exec api flask --app wsgi create-user --role OWNER`.
6. Sign in at http://localhost:5173; API health: http://localhost:8000/healthz.

The default Docker Compose binds ports to localhost and is **NOT internet-facing production TLS configuration**.

## Native development and verification

Requirements: Python 3.12+, Node 22+, PostgreSQL 16 and Redis. Install backend requirements under a virtual environment. Run `python -m pytest -q` from `backend/`; run `python -m flask --app wsgi db upgrade` and `python -m flask --app wsgi db check` against an isolated PostgreSQL schema. From `frontend/`, run `npm install && npm run build`. The GitHub verification workflow checks tests, compilation, TypeScript build, and migration upgrade/downgrade on PostgreSQL 16.

## Money and fiscal safety

1. Recording a tenant claim or receiving a provider initiation response **never** credits an invoice. Staff must verify cash/bank evidence separately; mobile collections require independent provider confirmation.
2. Each successful verified payment records an invoice credit and immutable ledger event in one database transaction. Failed/ambiguous callbacks remain pending or unreconciled.
3. Credit notes do not erase issued invoices. Accounting reversals restore balances without claiming real bank or mobile-money refunds.
4. Deposits are tracked as pending/approved hold, refund or withholding evidence. A recorded refund **does not transfer money**.
5. Internal PDF receipts are explicitly **not official URA fiscal receipts**. EFRIS requires a taxpayer-specific, approved URA adapter. Only authenticated acknowledgment may mark a submission accepted.
6. Encrypted backups must be transferred off the production VPS and restored periodically on isolated staging.

## Operations and outstanding requirements

See [delivery register](docs/DELIVERY_STATUS.md), [HostWares runbook](docs/HOSTWARES_DEPLOYMENT.md), [go-live acceptance](docs/GO_LIVE_CHECKLIST.md) and [operations](docs/OPERATIONS.md). Do not turn on third-party flags without sandbox verification. Final legal pages, UAT, approved staff credentials, verified legacy data and real-device testing require external signoff.

## Branching

Commit on `perez`, use reviewed PRs to merge into `main`. A successful PR merge means code is integrated, **not** that the product has been deployed or passed real-money and tax acceptance. Do not cut a production release tag before launch signoff.

## Property hierarchy, onboarding and financial workflows (November 2026)

- **Buildings / floors:** Create buildings under a property, create ground/basement/upper floors, place and move rooms with a reason. Cross-property room placements are rejected. Existing rooms without floors stay valid.
- **Account security:** In production the user console never shares an initial password. An owner sends a one-time email invitation; the user sets a password through `/account/activate`. Existing users can request a non-enumerating 30-minute recovery link at `/forgot-password`. Outbound email requires `SMTP_HOST`, `SMTP_PORT` (465/587 only), `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM`, and an approved `PUBLIC_APP_URL` (HTTPS outside localhost). Without email configuration, invitations fail closed.
- **Permission controls:** `/permissions` lists the persisted role permission matrix. Only a super administrator can change grants; no grant can exceed a server-side role ceiling. Run `flask --app wsgi seed-permissions` after introducing new protected routes.
- **Proration:** `/proration` previews actual-calendar-day rent with effective dated renewals. A finance officer must confirm that the contractual terms permit that policy before invoice issuance. Partial months are never automatically charged using an assumed formula.
- **Expense checks:** Expenses are `PENDING_APPROVAL` until a different authorized person approves or rejects the claim. Approved accounting expenses can be reversed by a distinct reviewer; reverse entries are immutable, and this does not send bank money. Previous expenses migrated from an unreviewed schema become `REVIEW_REQUIRED` rather than silently approved.
- **Annual trends:** `/trends` shows 12 months of verified settled collections, net invoices and approved expenses (incurred date), with accessible charts and a source-data table. Undated historical settlements are disclosed separately; these metrics are **not** a cashflow statement.

### Verification checks

Use `python -m pytest -q` for the SQLite-backed unit and API tests. The CI backend job also applies and rolls back all PostgreSQL migrations and then executes `tests/test_postgres_invariants.py` against a **disposable migrated PostgreSQL 16 database** via `TEST_POSTGRES_URL`; those tests verify PostgreSQL audit triggers and concurrent payment approval. The frontend job compiles React/TypeScript and performs a production build.

This is development verification. Never substitute green CI for legally approved leases, MTN/Airtel/URA onboarding, external malware checks, real backup restores, third-party callbacks, real-device accessibility, or operational UAT.

- **Audited portfolio editor:** `/portfolio-editor` searches and updates property, building, floor, and room listing fields; no overwrite of current signed lease amounts. `/room-placement` handles floor changes separately. PostgreSQL keeps the audit log append-only.
