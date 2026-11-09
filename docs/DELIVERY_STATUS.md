# Kats Property Management — implementation and acceptance register

Updated: 2026-11-09. The repository was initially empty. The blueprints comprise 15 implementation/operations phases. This table is based on files and automated test results; **no code can be certified 100% correct without broader integration, security, performance and user acceptance evidence**.

| Scope | Source implementation present | Remaining validation/dependency |
|---|---|---|
| Flask/React/PostgreSQL foundation | Yes: application, migration chain, local Docker, GitHub tests | HostWares staging/production and actual full-stack smoke/load testing |
| Authentication/session security | Argon2id, JWT+CSRF, refresh replay prevention, password-change invalidation | Real auth penetration review, password recovery/verified email workflow |
| Role matrix | Database role grants, seeding CLI, server ceilings, administrative API | Full permission UI and exhaustive endpoint/object-matrix testing |
| Properties and room lifecycle | Basic CRUD create/list, statuses and immutable history | Buildings/floors hierarchy, advanced room editing/search and UAT |
| Tenant onboarding | Staff provisioning, linking a tenant login, tenant self-rooms/lease | Invitation email identity proof, legacy import and verified data ownership |
| Leases and inspections | Active leases, renewals, effective rent changes, move-out inspection and termination | Document signatures, comprehensive inspection checklists and proration policy review |
| Billing and financial ledger | Recurring invoices, line items/charge types, credits, account balances, receipts | External source reconciliation, full deposit rules, tax/legal treatment, real concurrency testing |
| Cash and bank | Pending evidence, two-person review, ledger posting, accounting reversal | Real bank transfers/receipts verification and actual refund execution |
| Deposits | Hold/refund/withhold accounting, second-person approval and amount constraints | Verified settlement evidence and real disbursement/provider/bank flow |
| MTN/Airtel | Server-side adapters, status polling, strict amount/currency/reference matching, integration mock tests | Approved merchant accounts, official provider-contract schema acceptance, sandbox/live end-to-end tests |
| EFRIS | Durable fiscal outbox, structured approval adapter contract, retry/accepted proof validation | Approved URA-specific signing/encryption SDK or adapter, taxpayer config and fiscal acceptance |
| Documents | Signed S3-compatible private upload/download endpoints and UI | Object-storage credentials, malware scanning provider and private data retention |
| Notifications | In-app reminders with durable dedupe, scheduled lease expiry | SMS/email vendor integration, delivery verification and preferences |
| Maintenance/expenses | Basic workflows, work orders, status changes, expenses | Contractor approvals, complex cost reconciliation and UAT |
| Reporting | Cohort metrics, overdue aging, CSV/XLSX exports, PDF statements/internal receipts | Real bank cashflow, report-data reconciliation, advanced charting |
| Public site/legal/contact | Landing, public contact/demo intake, owner inbox, versioned publishable legal pages | Approved legal copy, privacy compliance and communication operations |
| Operational readiness | Encrypted backup/staging restore helpers, security middleware, migration and CI checks | Actual restore drill, TLS, offsite object storage, monitoring, incident drills, manual penetration and device testing |
| Code release | `perez` development changes and PR | GitHub merge verification and release management; no production tag without acceptance |

**Known code-level gaps and risks:** Building/floor hierarchy, full refund settlement, role-editor frontend, signed URA provider-specific adapter, customer messaging transports, invitations/reset email delivery, deep automated E2E/performance/security test coverage, and complete administrator workflow are not fully implemented or validated. These cannot honestly be relabeled infrastructure-only. Prioritize them before marketing this as production-ready.

All external integration flags remain OFF by default. See GO_LIVE_CHECKLIST.md for customer and infrastructure acceptance.
