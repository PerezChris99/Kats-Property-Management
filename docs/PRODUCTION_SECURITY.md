# Kats Properties — security and capacity acceptance

**Proprietary software, copyright © 2026 Kats Properties.** All rights reserved. The application is not open source. No automatic infringement fee is created by a notice; remedies require a lawful basis. See LICENSE.

## Protections implemented
- API request type, body-size and origin validation; secure cookies with CSRF; rate limits stored in Redis for production; structured no-store JSON API headers.
- Bounded database pools, statement and idle-transaction timeouts, limited pagination offsets, workload composite indexes and append-only finance/audit guards.
- PostgreSQL FORCE RLS on private DOCUMENTS ONLY, default deny, authenticated tenant/caretaker context set per SQL transaction. Other tenant/finance tables depend on server-side RBAC and object scoping, not universal RLS.
- Nginx size, rate, concurrency and upstream limits; hashed asset caching; no-store API; CSP; minimal diagnostic logging; non-root backend; gunicorn worker recycling.
- React escaping and short-lived in-flight GET coalescing; no persistent caching of tenant data; lazy-loading infrequent views.
- Container ignore rules exclude local databases, secrets and test artifacts. CI scans current tracked text for high-confidence credentials.

## Production operator requirements
1. **Keep the GitHub repository private.** A license cannot make publicly published source confidential. Audit collaborators/forks and rotate keys exposed in any past commit.
2. Use a trusted HTTPS-terminating reverse proxy. Only enable TRUST_PROXY_HEADERS when an audited proxy overwrites forwarded headers. Validate the actual client IP through HostWares/CDN, or per-IP rate limits may throttle an entire shared proxy.
3. Configure strong unique application/JWT secrets, COOKIE_SECURE=true, explicit HTTPS CORS origins, PostgreSQL, Redis, application URL and controlled provider feature flags. Do not turn on real payment/fiscal integrations without acceptance.
4. Database capacity: maximum API DB connections equal Gunicorn worker count times (DB_POOL_SIZE + DB_MAX_OVERFLOW), plus separate Celery, migration and admin sessions. Default 2 x (5+2) gives at most 14 API connections. Monitor real workloads before raising limits.
5. Apply new indexes to staging first, inspect query plans and consider CONCURRENTLY for large live tables. Indexes cost write throughput and storage; tune based on actual query profiles.
6. Use a separate least-privilege application DB role without SUPERUSER/BYPASSRLS. Force RLS currently covers documents only; wider RLS needs explicit staff/service policies and staging regression tests before activation. Migrations require a privileged role.
7. Keep secrets out of Git and images; configure request-log scrubbing, encrypted off-host backups and tested restores. HSTS and real TLS redirects belong at the PUBLIC edge, not the internal HTTP container.
8. Complete authenticated security, accessibility and performance tests, including IDOR, SQLi/XSS/CSRF/SSRF, brute-force, provider callbacks, queue backlog, worker recovery, load and resource limits, on real staging.
9. Keep rate limit, database, error, rollback and backup monitoring. Measure p95/p99 response times and query CPU before making 'instant' or high-scale performance claims.

## Explicit remaining work
Provider-specific fiscal integration, bank disbursements/refunds, external file-malware scanning, complete document signatures, SMS provider delivery, infrastructure TLS/monitoring, load and penetration tests and real customer UAT remain acceptance blockers. No finite code change can guarantee 100% security or performance.
