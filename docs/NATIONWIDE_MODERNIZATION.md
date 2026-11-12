# KATS Nationwide Product Modernization — implementation and evidence register

**Date:** 2026-11-12
**Status:** Rolling engineering program; NOT a production/go-live or multi-tenant certification.
**Source of truth:** This document plus [GO_LIVE_CHECKLIST.md](GO_LIVE_CHECKLIST.md).
**Git:** Commit to `perez` and merge to `main` only after checks. No new implementation branches.

## Product principles

1. UGX and Uganda-specific operating rules must not create local-quality UI or engineering.
2. Financial and legal outcomes require accountable human approval, traceable evidence, and independent verification.
3. All roles must have task-focused interfaces; API and SQL enforce permissions rather than navigation.
4. A green CI run is evidence of defined tests, not proof of customer acceptance, bank settlement, legal approval, or availability.
5. Do not turn on multi-organization signup until *every* customer-owned table and query is scoped and tested.
6. All new endpoints return only live database results; no fictional production KPIs.

## Status legend

- **Verified**: implementation exists AND relevant automated job passed on the referenced head.
- **Implemented / pending verification**: code committed; tests have not yet passed on current head.
- **Foundation only**: schema or design in place but deliberately not exposed as a commercial feature.
- **Pending**: not implemented.
- **External signoff**: requires verified third-party, infrastructure, professional or customer evidence.

## Current engineering tranche (PR #41)

| Item | Status | Files | Acceptance |
| --- | --- | --- | --- |
| Server-side table search | Implemented / pending verification | `backend/app/api.py`, `frontend/src/App.jsx` | Finds matches outside first page; literal SQL wildcards; tenant isolation; clear empty and failed states |
| Read-only payment consistency control | Implemented / pending verification | `backend/app/finance_health.py`, `frontend/src/FinanceHealthPage.jsx` | Finance-only permission; computed SQL exceptions; no mutations |
| Independent tenant dashboard/lease requests | Implemented / pending verification | `frontend/src/App.jsx` | One failed request does not hide the other's successful data |
| Legacy organization registry | Foundation only | `backend/app/organization_models.py`, migration 0028 | Existing business mapped to one org; no new public tenant creation or org-switch route |
| Tests | Implemented / pending verification | `backend/tests/test_{server_search,finance_health,org_registry}.py` | CI plus PostgreSQL migration roundtrip |

## Nationwide architecture: strict multi-organization launch gate

**Current application:** one property business. An organization registry alone does not make it SaaS.

**Safe organization rollout sequence:**

1. Inventory ALL customer-owned entities: users, invitations, roles, properties, buildings, floors, rooms, tenants, leases, invoices, payments, settlements, ledger history, expenses, maintenance, jobs, documents, notifications, utilities, audit, reports, exports and provider configuration.
2. Introduce `organization_id NOT NULL` with a staged, audited legacy backfill and composite organization-scoped foreign keys. Validate no orphan or cross-organization references.
3. Replace global `User.role` authorization with explicit organization memberships plus scoped capability grants. Reassess SUPER_ADMIN: platform operator privileges must not silently gain customer-finance read access.
4. Scope every read, write, aggregate, export, search, background task, file object and provider callback to a verified organization/actor context. Never accept client-supplied organization ownership without membership authorization.
5. Enforce Postgres RLS using a least-privileged runtime role, FORCE RLS, and independent policy tests. Transaction-local settings alone are insufficient against arbitrary SQL execution.
6. Build concurrent cross-organization tests for identical tenant names, overlapping property numbers, invoice numbers, provider references, callback replay, queue retries and file downloads.
7. Verify organization lifecycle: provisioning, invitations, suspended org, member removal, property agency transfers, archive/export, retention, plan changes, and failed payments. Prohibit global customer data searches.
8. Only after all tests pass: allow multiple independent organizations and configurable plan entitlements.

Do NOT enable this via one flag in the existing single-business code.

## Financial system: release-critical controls

| Component | Required implementation | Acceptance evidence |
| --- | --- | --- |
| Accrual accounting | Balanced journal, per-organization chart of accounts, period locks, corrections via reversals | Debits = credits for every posted transaction; append-only DB guard |
| Receipt application | One provider/cash/bank payment allocated safely across invoices and advance balances | Concurrent duplicate/retry tests; no money creation |
| Reconciliation | External bank/mobile statements matched with internal verification and financial postings | Signed/hashed statement import, unmatched queue, accountant approval |
| Deposits | Separate refundable liability account; approved hold/refund/withhold | Move-out statement; independent reviewer; verified bank payout |
| Owner settlements | Management-fee calculation, segregated owner payable balances, statement generation | Owner total equals bank/ledger records; dual approval |
| Expenses | Vendor registry, invoice evidence, payable approvals, settled disbursement checks | No payee changes after authorization; reversal trail |
| Fiscal | URA-specific EFRIS invoice and credit-note adapters | Official provider profile and taxpayer UAT; no false 'fiscalized' claims |

The reconciliation exceptions endpoint compares `Invoice.paid_ugx` to unreversed
`RECONCILED Payment` rows; it is **not** a real external bank reconciliation.

## API and backend modernization

- Split `app/api.py` into domain blueprints without breaking `/api/v1`.
- Publish OpenAPI 3.1 schemas with exact auth, pagination, idempotency and error contracts.
- Schema-validate request bodies and enforce canonical error codes, bounded payloads and stable 400/401/403/404/409/429 responses.
- Extend keyset pagination to high-volume search and history with an immutable stable ordering and scoped cursor.
- Retain modular monolith + Celery/Redis. Add job status, attempt history, dead-letter/manual replay and queue backpressure.
- Keep authorization at API, SQL and object layers; never trust hidden nav tabs.

## Role-specific product completion

**Owner/landlord:** portfolio drilldown, occupancy/vacancy aging, arrears aging, cash-vs-accrual disclosure, liabilities, owner distribution and contract renewal risk.

**Tenant:** current lease/signatures, receipts, payment status and allocation explanation, deposit liability, utilities proof, work-ticket updates, privacy choices and dispute escalation.

**Caretaker:** mobile-first task board, inspection/checklist, meter photo, offline *draft* queue with explicit user-approved replay and idempotency, urgent ticket SLA escalation.

**Agency:** separate owner roster, property management mandates, negotiated fees, owner portal, owner-scope statement, accounts payable and disbursement review.

**Administration:** least privilege, privilege expiry, user lifecycle, break-glass with audit, mandatory MFA enrollment, privacy request fulfillment and tenant deletion/hold policies.

## Frontend and UX governance

- Establish a single design-token source: typography, spacing, contrast, surfaces, tables, controls, states and responsive layouts.
- Decompose `src/App.jsx` into role/feature routes and independent page modules.
- Replace redundant CSS and `!important` overrides gradually with screenshot and accessibility regression tests.
- Server-side filtered search (current tranche) first; later add authenticated global search with per-object authorization, search rate limits and no cross-organization leaks.
- No blank screens. Loading, empty, errors, retry and stale-data signaling for every route.
- Replace generic CRUD forms with task-specific payment approval, move-in, renewal and contractor completion workflows.
- Test WCAG 2.2 AA against NVDA/VoiceOver plus keyboard, zoom, touch and reduced motion.
- Validate 360, 640, 768, 1024 and 1280px and short desktop viewports: navigation must never silently clip links.

## Property operations

- Asset inventory, service history, statutory inspection dates and contractor/vendor approval.
- Ticket SLA class and response/resolution timers, escalation and evidence of completion.
- Work order assignment, bid/quotation, approval, vendor expense, inspection/tenant acknowledgment and release.
- Utility meter evidence, tariff snapshots and shared-meter allocation rules (explicit consent/contract checks).
- Search and report across districts via validated region and address reference models, not free-text-only dashboards.

## Packaging and licensing (entitlements, not separate codebases)

| Edition | Customer | Entitlements (planned; not yet implemented) |
| --- | --- | --- |
| Essential | Individual landlord | Property, unit, lease, rent, basic work orders, tenant portal |
| Professional | Agency and multiple owners | Portfolio owner mapping, accounting controls, staff roles, reports, owner statements, integrations |
| Enterprise | Estate/institution | SSO, advanced approvals, SLA/audit, integrations, delegated operations, contractual support |

Plan selection must be enforced server-side, not by hiding React links. No invented subscription price or claim of entitlement enforcement before implementation. Proposed pricing requires customer research and actual operating cost analysis.

## Release, performance and privacy gates

- A named operations owner signs off DNS/TLS, managed PG/Redis, restricted credentials, encrypted offsite backups, point-in-time recovery, witnessed staging restore, rollback and incident playbooks.
- Run real authenticated load tests covering owner dashboard, tenant dashboard, invoice paging/search, payments, scheduled billing, maintenance and document uploads. Record p50/p95/p99, errors, DB locks, queue backlog and memory under the accepted traffic model.
- Confirm real MTN/Airtel merchant callbacks, banking reconciliation, SMTP/SMS delivery, S3/ClamAV and taxpayer-specific EFRIS profiles.
- Obtain Uganda legal review of tenancy, notices, data protection controller/processor obligations, tax obligations and financial payment flows. Keep evidence; code cannot self-certify.
- Require penetration testing, cross-organization IDOR tests, WCAG manual acceptance, mid-range Android/iPhone field acceptance, and signed customer UAT.
- Do not publish a 'nationwide production ready' badge until every P0 gate is signed and evidence linked.

## Work remaining after this tranche

**Pending code:** true multi-organization isolation; full balanced general ledger, payment allocations and bank imports; agency owner accounting; digital-signature/evidence lifecycle; field contractor workflow; notification delivery; asset registry; global search; full API contracts; modular frontend/backend refactor; authenticated load and browser acceptance.

**External:** merchant/fiscal/bank onboarding, domain/TLS, storage/antivirus, managed services, live backups, security audit, legal compliance and customer acceptance.

These are not cosmetic tasks and cannot honestly be marked complete by adding documentation or skeleton tables.

## Operations and capacity tranche (PR following phase 1)

- `GET /api/v1/operations/maintenance-aging` is read-only, restricted to staff,
  and uses SQL GROUP BY/CASE to classify open work by recorded priority and
  time since creation. It is an **age distribution, not a contractual SLA breach**.
  Its companion route presents the live chart with retry/empty/error states.
- `ops/load-workspace.js` provides k6 authenticated read-only staging load
  for OWNER and TENANT roles. It fails closed unless an approved HTTPS
  hostname containing staging/test and a disposable test-user cookie are supplied.
  No synthetic performance claim is made until results from a controlled
  staging run are saved and reviewed.
- Source changes do NOT constitute a deployed monitor, incident policy, legal
  certification or a completed contractor work-order workflow.

## Finance journal implementation tranche (2026-11-12)

- Alembic `0029_receipt_journal` introduces journal events and exactly two
  signed, positive-side debit/credit lines. PostgreSQL uses append-only
  triggers and a deferred constraint trigger that verifies balance at COMMIT,
  including cases where events and lines are flushed separately.
- Manual payment approval and independently verified provider settlement post
  `DR CASH_CLEARING / CR RENT_RECEIVABLE` atomically with the source payment
  and legacy ledger event. Accounting payment reversal posts the opposite
  journal, but only if the original payment was journaled. This avoids
  inventing a negative historical cash position for pre-journal payments.
- A restricted, read-only `/api/v1/finance/journal-control` endpoint reports
  account debits/credits and counts historical receipts not journaled. Owner
  and accountant UI explicitly identifies this as a receipt-event bridge.
- **Not complete:** invoice accrual posting, expenses, deposit liabilities,
  bank statements, payment allocations, owner payables, historical migration
  and financial period locks. No approved full double-entry GL or signed
  financial statement may be claimed before those workflows and evidence exist.

## Single-business property-mapping consistency (migration 0030)

The legacy organization registry now maps newly inserted PostgreSQL properties
through an AFTER INSERT trigger, in the same transaction that creates the
property. This addresses drift when the application creates new properties
after migration 0028's initial backfill. The trigger is explicitly **interim,
single-business only** and must be replaced by authenticated organization
ownership when genuine independent organizations are enabled. It is not an
authorization boundary; full multi-organization tenancy remains pending.
Local SQLite convenience fixtures do not certify this PostgreSQL trigger.
