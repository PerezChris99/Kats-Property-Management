# KATS Production Database and Performance Hardening

**Status:** source-level implementation and automated tests; **not live production acceptance**. KATS is currently a **single-owner** property-management application, not a tenant-isolated SaaS hosting unrelated landlords. Do not point development/demo tools at customer data.

## Changed security and performance contracts

| Layer | Hardening |
|---|---|
| PostgreSQL | Alembic `0026` adds 11 composite/lookup indexes and FORCE RLS for `tenants`, `leases`, `invoices`, `payments`, `maintenance_requests`, and `notifications`. Existing `documents` FORCE RLS remains. |
| Access / RBAC | Verified JWT/session version and account state select the application actor. The existing route permission matrix remains in force. Transaction-local `set_config(..., true)` sets PostgreSQL row scope for **every private API route**, not only document routes. |
| Scheduled jobs | Celery tasks use an explicit short-lived SERVICE row scope and clear it after execution. SQL connection pools never rely on session-level `SET` values. |
| Mutations | Payment/utility/fiscal idempotency and accounting approvals already existed. Alembic `0027` adds per-actor optional maintenance request fingerprints; sending the same key with identical data returns the original ticket. Mismatched retry payloads fail with 409. |
| High-volume reads | Existing server-bounded `page`/`page_size` still works (max 100 items, bounded offsets). `invoices`, `payments`, `maintenance`, `audit`, `notifications` optionally support signed one-hour keyset cursors: `?cursor=start&page_size=25`, then use `next_cursor`. A cursor is tied to the authenticated identity, endpoint and page size. |
| Privacy-safe caching | Private API and authenticated HTML remain `no-store`; only public, identity-independent legal/product metadata gets a 60-second conditional ETag cache. Browser PWA cache stores only a bounded set of same-origin static assets. |
| Bad networks | Frontend retries transient **GET only**, at most two additional attempts. All mutations remain single-shot; no automatic payment replay. Navigational fetches are abortable and stale responses are ignored. Offline routes show the fallback page rather than private stale records. |
| Availability | Production PostgreSQL connections require certificate hostname verification (`sslmode=verify-full`), bounded pools, 3.5s lock timeout, 15s statement timeout, pre-ping and idle-transaction cutoff. Redis-backed rate limiting is already enforced by production config. |

## Safe migration and privilege sequence

1. **Back up and restore-test first.** Use encrypted automated PostgreSQL physical backups/WAL with a defined and rehearsed RPO/RTO. Never assume a successful snapshot means recoverability.
2. **Provision separate roles:** schema owner/migrator, restricted API/worker runtime role (LOGIN, required table DML only, NO SUPERUSER/CREATEROLE/CREATEDB/BYPASSRLS), and a read-only monitoring role. Keep the migration role and its password out of application containers. Policies cannot defend against a database superuser or a compromised SQL role able to set the application-controlled session variables.
3. Confirm the database's CA chain and connect using a private hostname with `sslmode=verify-full`. Enforce TLS on Redis and ingress too; do not use public databases.
4. Run migrations with the **migration role**, using a separate approved migration window:
   `cd backend && python -m flask --app wsgi db upgrade`.
   `0026` creates normal transactional indexes and forced policies; on already large/live tables, plan an online `CREATE INDEX CONCURRENTLY` strategy first and reconcile existing indexes. Do **not** blindly run DDL under peak write load. `0027` adds nullable unique maintenance idempotency fingerprint. Migration must be performed once per release, not by every API replica at boot.
5. **Seed route permissions** with the schema owner/migration identity: `python -m flask --app wsgi seed-permissions`. Set up a distinct authorized bootstrap mechanism for the first production OWNER. Never enable or upload the demo one-click login.
6. Start the restricted runtime and run `python -m flask --app wsgi security-preflight` and `python -m app.release_preflight`. Both are fail-closed on missing RLS/migrations/role constraints. Run the read-only diagnostics in [production_readiness.sql](../backend/sql/production_readiness.sql), checking that all seven tables are forced and have the expected policies.
7. Execute backup/restore, transaction and API authorization, row-scope regression, flood and slow-client, mobile-network emulation, p95/p99 latency, payment/settlement concurrency, and disaster-recovery tests in staging using synthetic data. **Do not enable production until approved.**

## PostgreSQL row security: actual boundaries

- The restricted SQL role defaults to no visible rows in the six new RLS tables without a verified transaction-local actor scope. Signed-in TENANT users are scoped to their linked tenant/lease/invoice/payment/maintenance records and own notifications. CARETAKER uses assigned rooms for authorized operational rows. OWNER/MANAGER/ACCOUNTANT/SUPER_ADMIN follow the current single-company model.
- Worker SERVICE scope is set only by trusted Celery task execution, not by a request header or client parameter. Private document policies from `0017` remain active.
- **Not every application table has RLS.** `users`, `rooms`, `properties`, ledger history and several specialized domains still rely on server-side RBAC, object checks and PostgreSQL grants. More tables require separate tested policies before claiming universal RLS. For independent landlord organisations, build an explicit `organization_id` tenancy key, membership model, cross-table FKs and data migration first. Merely adding RLS does not create true multi-tenant isolation.
- The custom `kats.actor_role` PostgreSQL settings are application-controlled context, **not an unforgeable PostgreSQL principal**. Protect against SQL injection, use a non-owner role, restrict DML, test role boundaries and never grant general SQL execution to clients. Introduce separate database principals for workers vs HTTP if your threat model includes arbitrary SQL execution by a compromised API process.

## Operations and costs

- Keep API worker count, Celery concurrency and per-process `DB_POOL_SIZE + DB_MAX_OVERFLOW` within `DB_CONNECTION_BUDGET`, leaving 10 or more spare connections for recovery/administration. Start with measured load, not maximum worker counts. Increase capacity only after examining CPU saturation, slow queries, pool wait, lock contention, memory and Redis eviction.
- Use `EXPLAIN (ANALYZE, BUFFERS)` on **synthetic or reviewed read-only queries** and collect `pg_stat_statements` where the operator enables it. Indexes cost disk and write amplification; assess actual access patterns and remove unused duplicates only after evidence.
- Tune autovacuum and analyze thresholds for high-churn `payments`, `invoices`, `notifications` and `audit_logs` based on churn, not generic global settings. Audit history is append-only; implement age-based archival/partitioning and lawful retention only after operational review.
- Cache only public identity-independent content at shared edges. Never cache JWT/session cookies, signed S3 URLs, banking status, ledger data, tenant information or rights-affecting records in a shared or persistent browser cache.
- Repeated writes after a timeout require **idempotency keys** and reconciliation, never blind automatic retry. Provider callbacks need verified signatures and independent server-to-server settlement checks.
- Keep request logs free of querystrings and credentials; aggregate latency, error-rate, slow-SQL, provider latency, pool exhaustion, deadlocks and per-tenant authorization failures. No third-party performance numbers or availability guarantees are asserted by this change.

## Before release

**Still required:** independent PostgreSQL RLS integration run on the final migration and real restricted role; proof of TLS and private-network topology; live backup/restore; credential rotation; production MFA activation; storage and antivirus; real payment/EFRIS provider certification; external load testing with a known traffic model; accessibility and offline-device acceptance; Ugandan counsel review. Full readiness requires those approvals, not just code passing.

For deployment configuration use [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) and [PRODUCTION_SECURITY.md](PRODUCTION_SECURITY.md).
