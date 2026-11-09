# Kats Property Management — verified delivery register

Last updated: November 9, 2026. The two supplied blueprints define the product scope. The repository began completely empty; implementation is being performed on the perez development branch. No production environment is deployed.

| Workstream | Implemented in perez | Outstanding for actual acceptance |
| --- | --- | --- |
| Repository foundation | Flask/React monorepo, local Docker Compose, perez branch, GitHub build verification | Code review and production release controls |
| Public landing and PWA | Landing page, responsive navigation, install manifest, offline fallback | Final legal/contact content, real-device 3G/PWA tests |
| Access and roles | Argon2 password hashes, JWT cookie/CSRF, owner-created users, basic role and tenant-scope controls | Password reset, refresh-token revocation/rotation, complete stored permission matrix and security audit |
| Properties, rooms, tenants | Core create/list endpoints, room-state audit, basic React forms | Building/floor support, document storage, complete history, search and business rule edge cases |
| Leases and inspections | Create lease, caretaker assignments, move-out inspection, gated termination, room-state history | Renewal, deposit reconciliation/settlement, damage evidence/photos, partial periods, comprehensive concurrency testing |
| Billing and ledger | Invoice create, scheduled monthly rent generation, duplicate protection, posted ledger history | Additional charges, proration policy, credit notes, broad reconciliation and ledger completeness |
| Cash/bank payments | Pending review, two-person approval, idempotency, accounting reversal | Verified bank settlement evidence, complex adjustments, refunds, robust concurrency and reconciliation |
| MTN MoMo, Airtel Money | Explicitly disabled/not verified | Real provider adapters, approvals, credentials, callback signature/replay, sandbox and production tests |
| Receipts and EFRIS | Internal non-fiscal acknowledgement API | Official fiscal documents, PDF receipt rendering, URA eligibility, EFRIS API and credit notes |
| Maintenance and expenses | Maintenance creation, restricted transitions, basic expense records | Work orders, vendor tracking, actual completion evidence, expense approval, audit completeness |
| Reports | Invoice-period totals, occupancy, arrears aging, expense summary, restricted CSV export and React report page | Real cashflow, PDF/Excel exports, report totals vs verified source records, charts |
| Notifications | No verified delivery | SMS/email/in-app notifications, templates, retries and user preferences |
| Admin/finance portals | Owner user management, caretaker scopes, manager and finance routes | Full admin control center, role/permission editor, integration dashboard, queue monitoring |
| Security, performance and reliability | Server auth, CSRF, role checks, initial tests, PostgreSQL migration CI | Threat-model tests, dependency audit, rate/load benchmarks, formal five-pass review and UAT |
| Backup and deployment | Encrypted dump and guarded staging restore helpers, HostWares runbooks | Real offsite backup, witnessed restore drill, TLS, infrastructure, secrets and monitoring |
| Release | Development changes on perez | Reviewed merge to main, tags, staging rollout, landlord training and signoff |

Do not infer deployment, external payment success, fiscal acceptance or recovery readiness from a source file. Follow docs/GO_LIVE_CHECKLIST.md and docs/HOSTWARES_DEPLOYMENT.md before promoting any code to production.

Five mandatory independent review passes: correctness, security, performance, reliability and product/mobile UX. All critical/high/medium findings must be resolved before release.
