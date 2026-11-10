# Uganda rental-system autopilot — source implementation and remaining gates

**Updated:** 10 November 2026 · **No production go-live approval**

This is an evidence register, not a claim of 100% compliance. Automated CI
shows code compilation, functional regression tests and PostgreSQL migration
checks; no independent penetration-test, government approval, provider
contract, actual hosting, or real business signoff has been completed.

## Source implemented and CI exercised

| Scope | Confirmed implementation |
| --- | --- |
| Core rental records | Property/building/floor/room, tenants, fixed-term leases, inspection/termination, caretaker assignments |
| Uganda safeguards | Deposit ceiling allows zero deposit and blocks amounts above one month's rent; increased renewal rent needs 60-day recorded service metadata, default ≤10%, ≥12-month increase interval; contract exception requires separate review |
| Invoicing | Overlap protection on manually created and monthly rent lines, scheduled 100-lease batches, credit notes, effective-date proration, correction of void/credit tenant balance |
| Receipts | PDF acknowledging staff custody of in-person cash while still PENDING_REVIEW, not mislabelled as a fiscal receipt |
| Utilities | Room meter baseline, water/electricity consumption and tariff snapshot, bounded per-meter reading history, one-time finance approval into an unpaid period invoice |
| Access and data protection | Cookie JWT/CSRF, server roles/grants, FORCE RLS for private documents, encrypted TOTP with step replay check, protected tenant privacy requests and owner review |
| Private files | Content signature check, private ClamAV scan, S3 version pinning, quarantine/unavailable fail-closed state; scanner/storage infrastructure unverified |
| Performance | Source query indexes, bounded pagination, billing transaction batches, SQL arrears aggregation, optimized reminder joins, JSX lazy routes and Nginx edge caching |
| Deployment packaging | Isolated internal containers, public Caddy TLS edge, managed PostgreSQL/Redis dependency declaration, placeholder environment template; CI validates configuration |

## Remaining code work for full commercial feature completeness

1. End-to-end contract generation, landlord/tenant digital signature and legally
   admissible delivery proof. Current notices only store staff-attested metadata.
2. Periodic/weekly tenancy terms, lawful rent in advance, prepaid balances,
   overpayments, tenant transfers, service-charge agreement records and
   multi-invoice payment allocation.
3. Full move-out and dispute flow including ordinary-wear-and-tear policy,
   evidence review, objection windows and independent resolution.
4. Contractor bids, purchase orders, approved vendor/payee registry, recurrent
   preventive maintenance and building safety schedules.
5. Meter tariff history, shared-utility allocation, prepaid vendor token
   reconciliation, meter photo evidence and disputed reading corrections.
6. Full agency owner registry, management contracts, owner-scoped portals,
   management-fee accounting, per-owner statements and segregation of funds
   if operating as a third-party multi-landlord management agency.
7. Proper double-entry general ledger and external bank statement import,
   reconciliation, maker/checker remittances and actual payouts/refunds.
8. Scalable cursor pagination and streaming full exports where contractual
   volume requires more than the current paginated/limited displays.
9. Real-browser E2E journeys, complete authorization matrix, concurrent
   payment failure simulations and documented OWASP ASVS test-case evidence.
10. Scoped authentic notice issuance/delivery and complete DSAR export and
    lawful erasure execution beyond the manual review queue.

## Third-party, legal and infrastructure gates (cannot be marked code complete)

- Uganda law: Have qualified landlord/tenant counsel review tenancy templates,
  deposit/increase exceptions, legal notices, lawful possession and eviction,
  accessibility and any land/agency contractual requirements.
- URA: Confirm taxpayer-specific EFRIS invoice/receipt obligations, government
  registration, approved provider/adapter, fiscal credit/cancellation behavior,
  actual sandbox and live receipts.
- Mobile money/bank: Obtain MTN/Airtel merchant approvals, sign merchant
  agreements, verify real settlement/refunds/chargebacks and reconciliation.
- Personal data: Confirm Uganda PDPO controller/processor status, contracts,
  data retention/privacy rights and lawful transfer rules.
- Infrastructure: Obtain domain, actual HTTPS certificate, production secrets,
  private PostgreSQL/Redis, SMTP, monitored logs, real scanner/object store,
  offsite backup/PITR and witnessed restore/rollback.
- Assurance: Independent penetration test, accessibility and low-end mobile
  device acceptance, measured p95/p99 load, accountant reconciliation, tenant
  and owner UAT, emergency response and real service availability.

## Evidence required for a release

For each completed go-live checklist item, store: requirement ID, responsible
operator, environment, test command, test data provenance, expected outcome,
actual outcome, evidence URI, approval date and independent signoff. Do not
store raw passwords, financial keys, personal identification photos or
unredacted payment tokens in audit reports.

**No unchecked item is converted into a verified claim merely by a green CI.**
