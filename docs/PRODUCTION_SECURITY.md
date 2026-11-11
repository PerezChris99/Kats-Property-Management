# Kats Properties — security and capacity acceptance

**Proprietary software, copyright © 2026 Kats Properties.** All rights reserved. The application is not open source. No automatic infringement fee is created by a notice; remedies require a lawful basis. See LICENSE.

## Protections implemented
- API request type, body-size and origin validation; secure cookies with CSRF; rate limits stored in Redis for production; no-store JSON API headers for private data, with short conditional caching only for approved public pages.
- Bounded database pools, statement and idle-transaction timeouts, limited pagination offsets, workload composite indexes and append-only finance/audit guards.
- PostgreSQL FORCE RLS covers private documents and six additional core tables: tenants, leases, invoices, payments, maintenance requests and notifications (migrations 0017 and 0026). Verified actor context is transaction-local; API RBAC and object checks remain essential. Other tables are not universally RLS-protected.
- Nginx size, rate, concurrency and upstream limits; hashed asset caching; no-store API; CSP; minimal diagnostic logging; non-root backend; gunicorn worker recycling.
- React escaping, stale-request cancellation, in-flight GET coalescing, transient GET-only retries and no automatic mutation replay; no persistent caching of tenant data; bounded static-only PWA caching.
- Container ignore rules exclude local databases, secrets and test artifacts. CI scans current tracked text for high-confidence credentials.

## Production operator requirements
1. **Keep the GitHub repository private.** A license cannot make publicly published source confidential. Audit collaborators/forks and rotate keys exposed in any past commit.
2. Use a trusted HTTPS-terminating reverse proxy. Only enable TRUST_PROXY_HEADERS when an audited proxy overwrites forwarded headers. Validate the actual client IP through HostWares/CDN, or per-IP rate limits may throttle an entire shared proxy.
3. Configure strong unique application/JWT secrets, COOKIE_SECURE=true, explicit HTTPS CORS origins, PostgreSQL, Redis, application URL and controlled provider feature flags. Do not turn on real payment/fiscal integrations without acceptance.
4. Database capacity: maximum API DB connections equal Gunicorn worker count times (DB_POOL_SIZE + DB_MAX_OVERFLOW), plus separate Celery, migration and admin sessions. Default 2 x (5+2) gives at most 14 API connections. Monitor real workloads before raising limits.
5. Apply new indexes to staging first, inspect query plans and consider CONCURRENTLY for large live tables. Indexes cost write throughput and storage; tune based on actual query profiles.
6. Use a separate least-privilege PostgreSQL runtime role without SUPERUSER/BYPASSRLS or schema ownership, with only necessary table grants. Seven core tables must have FORCE RLS and the correct policies before launch; execute the documented security and read-only release preflights. Other tables still depend on API object checks and database grants. Migrations require a distinct privileged role.
7. Keep secrets out of Git and images; configure request-log scrubbing, encrypted off-host backups and tested restores. HSTS and real TLS redirects belong at the PUBLIC edge, not the internal HTTP container.
8. Complete authenticated security, accessibility and performance tests, including IDOR, SQLi/XSS/CSRF/SSRF, brute-force, provider callbacks, queue backlog, worker recovery, load and resource limits, on real staging.
9. Keep rate limit, database, error, rollback and backup monitoring. Measure p95/p99 response times and query CPU before making 'instant' or high-scale performance claims.

## Explicit remaining work
Provider-specific fiscal integration, bank disbursements/refunds, external file-malware scanning, complete document signatures, SMS provider delivery, infrastructure TLS/monitoring, load and penetration tests and real customer UAT remain acceptance blockers. No finite code change can guarantee 100% security or performance.
