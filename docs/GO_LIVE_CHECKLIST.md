# Launch signoff checklist

The owner must approve this checklist based on evidence; source code alone does not close any item.

- [ ] Required landlord, manager, caretaker, accountant, tenant and developer workflows are complete and demonstrated.
- [ ] Staff and tenant permissions undergo object-level access and session security testing.
- [ ] Concurrent lease creation, scheduled invoicing, partial payments and idempotency are tested against PostgreSQL.
- [ ] Cash approvals, bank proof review, reconciliation, reversals, refunds and deposit settlement verified.
- [ ] MTN MoMo onboarding, callback signatures, pending/failed/success outcomes and sandbox reconciliation complete.
- [ ] Airtel Money onboarding, callback signatures, pending/failed/success outcomes and sandbox reconciliation complete.
- [ ] URA / accountant has confirmed the client's applicable EFRIS obligations and sandbox fiscalization/credit notes pass.
- [ ] Validate instant written in-person cash custody receipt delivery and distinguish it from accountant-approved receipts and official URA fiscal documents.
- [ ] Fiscal and ordinary receipt PDFs, tenant statements and exports reconcile with system ledger and external statements.
- [ ] Verify meter baseline, consumption, maker/checker approval, disputed utility tariffs and each bill against lease terms.
- [ ] Validate rent-increase notices, delivery evidence, lease exceptions, deposit 0-to-one-month policy and accounting reversals.
- [ ] Inspections, maintenance closure, move-out, notifications, attachments and legal pages work with actual roles.
- [ ] Former/current tenants can submit scoped disputes, receive reviewed responses, and escalate appropriately; human adjudication and local statutory procedures verified.
- [ ] Recurring preventive-maintenance plans generate exactly one actionable task per due date under worker failure/retry, with caretaker visibility, pause/retire tests and contractor handoff.
- [ ] Mobile performance and accessibility verified at 360px, on mid-range Android and an iPhone.
- [ ] All privileged accounts enrolled and recovered with MFA, securely protected encryption key and human-approved recovery process.
- [ ] Data protection requests independently fulfilled; privacy counsel/PDPO registration or applicability reviewed.
- [ ] Private S3 versioning + ClamAV tested against real storage; corrupted, oversize and infected content stays inaccessible.
- [ ] Load, dependency scanning, auth attacks, file-upload attacks and authorization tests show no outstanding critical/high/medium risk.
- [ ] Encrypted offsite backups, witnessed staging restore, rollback and on-call monitoring have evidence.
- [ ] Staging and production domains, TLS, secure DNS, restricted managed Postgres/Redis and secrets configured using docs/PRODUCTION_DEPLOYMENT.md.
- [ ] Read-only production preflight passes with a restricted runtime role against schema head, FORCE RLS/policies on all seven core private tables, verified PostgreSQL TLS and Redis. CI green is not equivalent to deployment approval.
- [ ] Real browser → API → database readiness is confirmed through the public domain (not an SPA fallback or mocked API).
- [ ] Graceful API/worker shutdown verified during a rolling deploy with no lost committed records or duplicated retries.
- [ ] Owner reviews access requests and sends separate one-time invitations; public requests never create accounts.
- [ ] Legacy balances and verified opening data imported and reconciled.
- [ ] Landlord and staff training, support plan, post-go-live monitoring and consent/legal notices approved.
- [ ] Five-pass review recorded: correctness, security, performance, reliability and mobile product quality.
- [ ] Reviewed perez changes merged to main; release tag created only for an approved release.

**No go-live signoffs are currently recorded.**
