# KATS — Single-Owner Production Modernization Register

**Owner model:** One private property-management business. This is NOT a SaaS, marketplace, or multi-customer platform.  
**Scope:** One owner-controlled installation can manage many properties, units, tenants, caretakers, accountants and authorized staff throughout Uganda.  
**Git workflow:** Push to `perez`; merge verified pull requests into `main`; synchronize the two existing branches.  
**Readiness:** Production approval depends on evidence; passing CI alone does not establish live deployment, legal compliance or accurate bank settlement.

## Architecture decision — binding

1. Use the existing React frontend, Flask modular monolith, PostgreSQL, Redis/Celery and PWA. Avoid separate microservices and unnecessary SaaS abstractions.
2. Keep a **single business owner** and role-based authorization. Property-level assignment and least-privilege tenant/caretaker access still matter.
3. No independent organization onboarding, multi-tenant data isolation, subscription billing, paid editions, pricing tiers, feature entitlements, agency-as-customer portals, or platform-operator tenant switching.
4. Existing organization tables (migrations 0028 and 0030) are **historical dormant metadata only**. Do not destructively drop them or remove migration history: doing so can break existing databases. New properties are mapped to the one legacy organization. No user-facing organization management should be added.
5. Agency billing and multi-owner payouts are **out of scope** unless this single owner subsequently signs contracts to manage assets for external owners.
6. Prior nationwide multi-organization/SaaS advice is superseded by this decision. Nationwide means *the owner's properties can exist anywhere in Uganda*, not that many companies can subscribe.

## Verified source implementations before this decision

| Capability | State | Notes |
| --- | --- | --- |
| Scoped global / table search | Verified | Staff and tenant access controls apply |
| Independent tenant dashboard requests | Verified | Partial API failure does not suppress successful information |
| Rent receipt journal | Verified bridge | Balanced immutable new receipt/reversal entries, NOT a complete general ledger |
| Reconciliation exception diagnostics | Verified | Internal ledger/payment consistency, NOT bank reconciliation |
| Maintenance aging | Verified | Time-open classification, NOT a contractual SLA measurement |
| Dormant one-business mapping | Verified | Single-owner business only |
| Browser, backend/PostgreSQL and Windows checks | Verified on prior merged heads | Re-run on every new head |

## Remaining owner-specific engineering work

**P0 — Financial integrity**
- Finish rent accrual and expense/deposit liability ledger postings, accounting periods, controlled adjustments, cash versus invoice reporting, and reviewed historical migration.
- Add verifiable cash / mobile-money / bank statement imports with deduplication, matching, exception queues and human approval. Never claim an unverified provider authorization is settled.
- Strengthen payment idempotency, concurrency, partial payments, advance payments and receipt allocation without creating/deleting money.
- Provide verified bank settlement totals, outstanding invoices, overdue aging, deposits held and operating cash flow in separate clearly named views.
- Require approved reversals with independent actors and immutable logs. Keep the owner able to review everything, with protections for irreversible real-world transfers.

**P0 — Security and reliability**
- Enforce MFA for privileged users in production, secure account recovery, rate limits, session revocation and object-level permissions.
- Verify PostgreSQL runtime least privilege, tenant-scoped RLS, document storage security, malware scanning, backups and retention policies.
- Run authenticated full-workflow load tests, migration upgrade/downgrade tests, incident and rollback drills, and witnessed offsite restore.
- Provide structured logging, error alerting, queue-depth alarms, background-job recovery and operational runbooks.

**P1 — Owner/tenant/caretaker operations**
- Owner: profitability, aging arrears, expiring leases, occupancy, vacancy, expenses, collections and live report exports.
- Tenant: secure lease/receipt/download access, notices, deposit tracking, maintenance tracking, disputes and move-out requests.
- Caretaker: phone-first assigned jobs, evidence, inspections, asset/utility readings, SLA notifications and explicit offline draft sync.
- Maintenance: contractor/vendor records, work-order approval/evidence, asset history and actual repair costs by property.

**P1 — Software structure and UX**
- Decompose oversized React and Flask modules into domain components/blueprints while preserving existing `/api/v1` contracts.
- Consolidate design tokens, eliminate redundant styling, remove dead code only with regression proof, improve responsive navigation and native accessibility.
- Produce API contracts and enforce consistent validation and pagination; never lose role-scoped search behavior.
- Measure dashboard speed and usable performance on mid-range Android phones and modest network links.

**P2 — Owner-specific enhancements**
- Regional/district reports for *this owner's* properties, optional additional staff roles, a read-only accountant export, and integration with the owner's actual bank/payment providers.
- Advanced forecasting can be added once real historical data supports it. Avoid fabricated KPI numbers and decorative AI.

## Explicitly excluded

| Exclusion | Reason |
| --- | --- |
| Independent customer organizations and memberships as a product | One-off owner system |
| SaaS tenant provisioning / onboarding | No external subscribers |
| Subscription billing, plan entitlements, pricing tiers | No commercialization as SaaS |
| White-label customer portals or cross-company administration | No external organizations |
| Multi-agency business architecture | No independent agency customers |
| Separate microservices and platform marketplace | Unnecessary operational complexity |

The existing dormant organization metadata may remain to preserve migration compatibility; it does not become a product requirement.

## External acceptance (not code-completable)

- Actual MTN/Airtel/bank integration credentials, settlement evidence and provider approvals where applicable.
- URA fiscal/tax-specific review and EFRIS production checks if applicable to the owner.
- Owner's privacy/data protection legal assessment, tenant notices, lawful retention and handling procedures.
- Production DNS/TLS, hosting, managed database, storage, scanned documents, SMTP/SMS delivery and operational monitoring.
- Offsite backup restore test, independent security assessment, real tenant/caretaker UAT and Android/iOS device testing.

## Completion rules

Mark an engineering item **complete** only after implementation, automated tests, real PostgreSQL migration validation, browser and Windows regression checks and a merged PR. Mark an external item complete only after third-party or deployment evidence. Never call KATS fully production-approved while financial correctness, backup recovery or live provider verification is unknown.

## Current owner-focused implementation

The next tranche adds role-restricted rent arrears aging and paged unpaid invoices in Uganda local time. The report shows **invoice debt**, never verified cash or bank settlement. Keep that distinction visible on every chart and export.

## Owner property equipment register (implementation tranche)

A dedicated `property_assets` inventory now records equipment, optional unit association,
condition and next service date. Owner/manager/superadmin can create and update assets
with an audit reason; accountant access is read-only, and caretakers can only read
assets explicitly associated with rooms assigned to them. Tenants cannot access
this administrative register. These are **equipment facts**, not SLA promises or
proof that a contractor has completed servicing.

The register intentionally does not create contractor payments or purchase
commitments; those require verified accounting and approval workflows.

## Production release MFA hard gate

The production-only `python -m app.release_preflight` now rejects approval
when no active owner account exists or any active OWNER, SUPER_ADMIN, MANAGER
or ACCOUNTANT lacks an enabled MFA enrollment and stored encrypted secret.
Inactive accounts do not block rollout. The gate does **not** disable,
enroll or modify any account, so administrators must enroll privileged
users through the existing MFA workflow before requesting release approval.
The gate is not a substitute for manual challenge/recovery testing or
independent authentication penetration testing.
