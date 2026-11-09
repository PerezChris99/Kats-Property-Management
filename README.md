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
