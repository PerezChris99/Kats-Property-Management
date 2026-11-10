# Kats Property Management — truthful implementation and acceptance register

**Updated:** November 10, 2026. Code is built around Flask/React/PostgreSQL and a single Ugandan property business. Implementation is reviewed against supplied blueprints, but **neither production deployment nor 100% correctness has been certified**.

| Scope | Implementation in source | Validation and remaining dependency |
|---|---|---|
| Foundation | Docker development stack, Flask/React, SQLAlchemy/PostgreSQL schema through 0015, Redis/Celery workers, PWA | Actual HostWares TLS deployment, backup restore and external observability |
| Accounts/security | Argon2id, short-lived JWT/CSRF, one-time refresh rotation/revocation; hashed invitation/reset tokens, 30-minute recovery, SMTP TLS sender | Approved public domain, transactional SMTP credentials/deliverability, real auth/security UAT |
| Roles | Server role ceilings, stored grant matrix, seed-permissions CLI, owner/superadmin permission editor | Whole-endpoint object-level penetration matrix and policy/tenant ownership verification |
| Property portfolio | Properties, buildings, floors, room placement, bounded search, auditable editing of listing/property metadata; backward-compatible legacy rooms | Owner-reviewed actual portfolio records, comprehensive archival/merge policies and multi-device UAT |
| Tenant onboarding | Owner invitations instead of emailed passwords, tenant user linking, scoped tenant account, private documents | Active mail provider, verified account ownership, actual legacy data import |
| Leases and inspection | Lease creation, renewals, default 60-day rent increase notice records, ≤10% annual increase policy, optional deposit up to one month, scoped inspections | Contract exception review, legal service proof, signed tenancy agreements, real owner/tenant acceptance |
| Rent billing | Monthly idempotent full-month invoicing in 100-lease batches, nonoverlapping rent lines, credit notes, proration and corrected tenant balances | Advanced advance-rent allocations, approved terms, fiscal settlement and real accountant UAT |
| Collection ledger | Two-person manual approval, verified-provider posting, reversal events and PostgreSQL append-only guard | Real bank evidence and reconciliations, production-provider webhook/settlement cases |
| Deposit records | Idempotent hold/refund/withhold with secondary review and move-out inspection checks | Bank payout/disbursement rails, settlement evidence and governing deposit policy |
| MTN/Airtel | Disabled-by-default initiation/status adapters, independent amount/currency/reference checks, retry polling | Merchant onboarding, validated official Airtel profile schema, sandbox/live settlement tests |
| URA EFRIS | Durable fiscal outbox with retry, adapter contract and verified fiscal-response requirements | **Taxpayer-specific URA certified connector/signing**, fiscal credit-note requirements and test taxpayer |
| Expenses | Pending, independent approval/rejection/reversal, append-only expense event history; legacy expenses flagged REVIEW_REQUIRED | Supplier evidence, real bank disbursement checks and account-owner UAT |
| Reporting | Invoice cohort, arrears, PDFs/XLSX/CSV, annual verified-settlement, invoicing and approved-cost charts | Real financial-statement reconciliation, historical migration, detailed accountant signoff |
| Maintenance | Caretaker scoping, job statuses, work orders, basic recurring plans, idempotent daily scheduled tickets and costs | Contractor/payee verification, safety inspection regulations and field acceptance |
| Documents | Tenant-scoped presigned S3-compatible private files, signed immutable object versions, MIME magic and ClamAV fail-closed scan before download | Real private S3 versioning and ClamAV, independent scanner tests, retention/legal approval |
| Messages | In-app alerts and scheduled reminders, resilient record model | SMS/email provider handoff and verified delivery, template/privacy consent |
| Admin/marketing | Role permissions, TOTP opt-in MFA, encrypted authenticator secrets, personal-data access/correction/erasure triage, versioned legal pages, demo inquiry inbox | MFA enrollment/recovery and privacy-registration procedures, approved wording, provider oversight |
| Testing | Current Python tests, frontend JavaScript lint and API regression tests, React JSX production build, PostgreSQL 16 migration round-trip, PostgreSQL concurrency and audit-trigger tests | Comprehensive external E2E, security/load tests, mobile/iOS/Android devices and genuine UAT |
| Release | JSX-only frontend; Caddy HTTPS/isolated production Compose + separate managed PostgreSQL/Redis packaging, CI syntax validation | Not deployed; DNS, mail, storage, backups, fiscal/payment integrations and production acceptance remain |

| Utility management | Water/electricity meters, integer consumption snapshots, caretaker readings, independent invoice approval and tenant-scoped visibility | Meter photo evidence, tariffs/contract review, shared-utility policies, field UAT |
| Receipts | Written cash custody receipt available before independent settlement; internal non-fiscal acknowledgements | Printer/on-site delivery acceptance and official URA fiscal receipt integration |
| Privacy | Owner-managed user requests for access, correction, erasure, restriction and objection | Approved PDPO processes, lawful identity validation, responses and any lawful deletion |
| Tenant disputes | Role-scoped rental complaints, chronological comments, owner/manager internal resolutions, written reopening history | Independent dispute adjudication, legal remedies, notice service, evidence files and owner acceptance |

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


## Additional verified source implementation — November 10

See [UGANDA_AUTOPILOT_REGISTER.md](UGANDA_AUTOPILOT_REGISTER.md) for exact
code-only completions and the remaining operator/provider dependencies.
The repository is **not certified** under OWASP ASVS or ISO 27001. MFA
enrollment is opt-in until every required operator actually activates it.
The production container definition is a *deployable configuration*, not
proof of actual DNS, TLS, managed services or go-live. Legacy unscanned
document objects remain inaccessible until verified.
