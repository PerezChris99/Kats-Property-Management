# Kats Property Management — truthful implementation and acceptance register

**Updated:** November 9, 2026. Code is built around Flask/React/PostgreSQL and a single Ugandan property business. Implementation is reviewed against supplied blueprints, but **neither production deployment nor 100% correctness has been certified**.

| Scope | Implementation in source | Validation and remaining dependency |
|---|---|---|
| Foundation | Docker development stack, Flask/React, SQLAlchemy/PostgreSQL schema through 0015, Redis/Celery workers, PWA | Actual HostWares TLS deployment, backup restore and external observability |
| Accounts/security | Argon2id, short-lived JWT/CSRF, one-time refresh rotation/revocation; hashed invitation/reset tokens, 30-minute recovery, SMTP TLS sender | Approved public domain, transactional SMTP credentials/deliverability, real auth/security UAT |
| Roles | Server role ceilings, stored grant matrix, seed-permissions CLI, owner/superadmin permission editor | Whole-endpoint object-level penetration matrix and policy/tenant ownership verification |
| Property portfolio | Properties, buildings, floors, room placement, bounded search, auditable editing of listing/property metadata; backward-compatible legacy rooms | Owner-reviewed actual portfolio records, comprehensive archival/merge policies and multi-device UAT |
| Tenant onboarding | Owner invitations instead of emailed passwords, tenant user linking, scoped tenant account, private documents | Active mail provider, verified account ownership, actual legacy data import |
| Leases and inspection | Lease creation, renewals, effective-dated rent, scoped inspections, termination safeguards | Signed-lease terms, inspection photo/evidence storage, owner acceptance |
| Rent billing | Monthly idempotent full-month invoicing, line items, credit notes, manual proration preview and confirmed issuance | Lease-specific calendar-day policy approval, edge-case UAT and payment-provider acceptance |
| Collection ledger | Two-person manual approval, verified-provider posting, reversal events and PostgreSQL append-only guard | Real bank evidence and reconciliations, production-provider webhook/settlement cases |
| Deposit records | Idempotent hold/refund/withhold with secondary review and move-out inspection checks | Bank payout/disbursement rails, settlement evidence and governing deposit policy |
| MTN/Airtel | Disabled-by-default initiation/status adapters, independent amount/currency/reference checks, retry polling | Merchant onboarding, validated official Airtel profile schema, sandbox/live settlement tests |
| URA EFRIS | Durable fiscal outbox with retry, adapter contract and verified fiscal-response requirements | **Taxpayer-specific URA certified connector/signing**, fiscal credit-note requirements and test taxpayer |
| Expenses | Pending, independent approval/rejection/reversal, append-only expense event history; legacy expenses flagged REVIEW_REQUIRED | Supplier evidence, real bank disbursement checks and account-owner UAT |
| Reporting | Invoice cohort, arrears, PDFs/XLSX/CSV, annual verified-settlement, invoicing and approved-cost charts | Real financial-statement reconciliation, historical migration, detailed accountant signoff |
| Maintenance | Caretaker scoping, job statuses, work orders, costs and repair record | Contractor/payee acceptance and evidence |
| Documents | Tenant-scoped presigned S3-compatible private files and downloads | S3-compatible storage, CORS, anti-malware validation, data retention/legal approval |
| Messages | In-app alerts and scheduled reminders, resilient record model | SMS/email provider handoff and verified delivery, template/privacy consent |
| Admin/marketing | Role permissions, security settings, versioned/publishable legal notices, demo inquiry inbox | Approved legal wording, email and production oversight |
| Testing | Current Python/React tests, PostgreSQL 16 migration round-trip, PostgreSQL concurrency and audit-trigger tests | Comprehensive external E2E, security/load tests, mobile/iOS/Android devices and genuine UAT |
| Release | Development work committed to perez and PR-reviewed into main after green checks | Never release/deploy without full signoffs |

## Security baseline and known limitations

The repository includes proprietary Kats Properties ownership notices, bounded API request/rate controls, Redis rate-limit storage in production, verified-cookie authentication and role grants, database query/pool bounds, indexed paginated lists and PostgreSQL FORCE RLS on private document rows. All new sensitive routes are subject to anonymous-route regression checks. A CI scanner checks high-confidence secret signatures in the current source tree.

This does **not** prove secrets were never exposed historically; any leaked credentials need rotation. Database RLS applies to **documents only**, while financial and other tenant records rely on server-side RBAC and object-level checks. An external security review, provider credentials, production monitoring, scale/load tests and backup restore drills remain required.

## Outstanding code-level caveats

This is **not** purely a third-party/infrastructure checklist yet. Portfolio archival/bulk editing, full signed document workflows, provider-specific EFRIS/fiscal-credit adapter requirements, bank refund/disbursement implementation, SMS/email notification delivery workers, exhaustive security/end-to-end coverage and detailed contractor/bank reconciliation remain incomplete or unverified. Some depend on provider specs and contractual decisions, but until implemented and tested they are not ready to be certified 100%.

No test result is a guarantee of error-free operation. When integrations are disabled the app must continue operating in a visibly non-settled, non-fiscal mode. Consult GO_LIVE_CHECKLIST.md before accepting real money or issuing official fiscal documents.

## Security and performance controls (2026-11-09 hardening pass)

The application now includes a Kats Properties proprietary license, validated JSON and
request bodies, CORS origin rejection, no-store private API responses, security headers,
bounded Nginx requests/connections, Nginx gzip/static immutable assets, Redis-backed
multiworker rate limits, and bounded SQLAlchemy/psycopg connection pools. API data
views support bounded page sizes and optional exact-count suppression; the React
resource interface has server-side page navigation and in-flight GET coalescing.

The database has 14 additional workload-focused composite indexes and a forced
PostgreSQL row security policy for **private documents** scoped by verified
tenant/caretaker identity. It does not falsely claim RLS is enabled on every
table or that a superuser cannot bypass RLS.

**Must still verify before production:** use a restricted non-superuser DB role,
configure only a sanitized trusted proxy for X-Forwarded IP, test TLS/HSTS at
the actual public ingress, provision independent Redis limiter storage,
benchmark p95/p99 latency and PostgreSQL connections with realistic data,
review all endpoint authorization cases, verify restore/monitoring/alerts,
and commission a penetration test. See docs/PRODUCTION_SECURITY.md.
