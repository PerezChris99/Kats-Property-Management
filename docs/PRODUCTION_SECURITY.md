# Production security and performance baseline

**Kats Property Management — proprietary software of Kats Properties.**

This runbook documents enforced source controls separately from settings that
require deployment. The system is *not* proven 100% secure or infinitely
scalable; no real production load, penetration test or disaster recovery
exercise has been completed.

## 1. Rights and repository visibility

The source is **not open source**. [LICENSE](../LICENSE) reserves all rights
to Kats Properties and prohibits unauthorized third-party use. The GitHub
repository was **public when checked on November 9, 2026**. A restrictive
license does not make source unreadable. An authorized repository administrator
should review **GitHub → Settings → General → Danger Zone → Change repository
visibility** and set it private if public access is unintended. Changing
visibility may affect external deployments/CI integrations and should be
coordinated.

## 2. Trusted edge, transport, and rate limits

- Serve the site through an external **HTTPS ingress**; never expose the
  Docker Compose development HTTP endpoints to the Internet.
- Configure TLS 1.2+ and TLS 1.3, HSTS (and trusted certificate renewal)
  at the *real public TLS terminator*. Nginx inside the project currently
  serves HTTP to that trusted terminator.
- Nginx strips incoming forwarding headers before sending to Gunicorn,
  bounds bodies to 512 KiB, imposes timeouts and per-client request/concurrent
  limits, compresses text, and caches content-addressed assets.
- If and ONLY if the API is reachable exclusively through the trusted
  Nginx edge, configure both TRUST_PROXY_HEADERS=true and
  APP_BEHIND_TRUSTED_PROXY=true on the API. Never trust arbitrary
  X-Forwarded-For on an exposed public Gunicorn port.
- Configure exact HTTPS CORS_ORIGINS, trusted hostname list TRUSTED_HOSTS,
  and secure cookies. No wildcard origins with credentials.
- Production requires distributed Redis-based Flask-Limiter storage
  (RATELIMIT_STORAGE_URI or REDIS_URL). Memory rate limiting is not
  sufficient for Gunicorn/multiple replicas. Test fail-closed behavior when
  Redis is unavailable; budget rate limits for users behind shared NAT IPs.
- Strict script CSP denies unsafe-inline JavaScript. Current inline React
  style attributes require style-src 'unsafe-inline'; remove those styles
  before enabling stricter style CSP. Avoid dangerouslySetInnerHTML and
  render legal/user fields as escaped React text.
- Do not enable broad HTTP caching for authenticated API JSON or generated
  PDF receipt/statement responses. All private API responses are no-store.

## 3. Database resource budget

Default application PostgreSQL pool: pool_size 5, max_overflow 2, pool_timeout
10 seconds, pool_recycle 1800 seconds, LIFO, pre-ping. This is **per Gunicorn
worker/process**, not a global pool. For two workers the API can open up to
14 concurrent database connections. Add Celery workers, scheduled jobs, and
administration processes when calculating the full PostgreSQL max_connections.

The PostgreSQL driver enforces statement_timeout=15s and
idle_in_transaction_session_timeout=30s. Review individual long reports
against realistic production volumes; don't indiscriminately increase
timeouts. Use a PgBouncer transaction pool when actual connection pressure
and deployment topology justify it, then test compatibility with SET LOCAL,
prepared statements, migrations and transaction-bound RLS policies.

Versioned migration 0016 adds 14 composite indexes for invoices,
collections, property/room state, expenses, maintenance, notification inbox,
private documents and audit access. Indexes speed reads but increase
storage/write/vacuum overhead. Monitor pg_stat_statements, cache hit ratio,
vacuum progress, index scan counts and query plans after deployment;
remove unused indexes based on evidence.

API list endpoints cap pages at 200, page size at 100 and offset at 10,000.
Clients can use include_total=0 to omit an expensive exact COUNT. For
datasets larger than this, implement task-specific keyset pagination and
filtering rather than lifting the cap.

## 4. Database RBAC and row-level security

Role ceilings, persisted route permissions and tenant/caretaker object scope
remain mandatory at the API. Migration 0017 additionally enables and
**FORCES** RLS for the private **documents** table. Its policy allows:

- Owner, manager, accountant and super-admin records under a verified role.
- Tenants: only documents for their linked tenant ID.
- Caretakers: only permitted document categories on currently assigned rooms.

The verified Flask identity is mapped to transaction-local PostgreSQL
kats.actor_role, kats.actor_user_id and kats.actor_tenant_id GUCs. SET LOCAL
is reinstalled on new transactions and must never be replaced by
session-persistent SET, which would leak scope through pooled connections.

For production, the API must connect as a **dedicated non-superuser,
non-BYPASSRLS runtime database role**, not the schema-migrating DBA. The
runtime role requires SELECT on caretaker_assignments because the document
policy uses a subquery. PostgreSQL superusers and BYPASSRLS roles always
bypass policies. Use a separately privileged migration/backup role,
and check grants, row security and backups at staging before go-live.

**Coverage boundary:** the other tables still rely on API object authorization
and are not all protected by database RLS. Do not advertise full-table RLS
without implementing and testing separate policies.

## 5. Secret and PII controls

- Store production credentials in a trusted secret manager or restricted
  runtime environment, not source control, client-side VITE_* variables,
  Docker build context, server logs, URL query parameters, screenshots or
  backup archives.
- Backend and frontend .dockerignore files exclude local .env, keys,
  logs, test data and unnecessary artifacts from image builds.
- Production Flask error handling logs exception type and endpoint name,
  never request body, query text or exception values. Nginx access logs are
  disabled by default; arrange sanitized monitoring externally.
- Rotate leaked/revoked credentials immediately; do not simply delete
  leaked commit history and assume tokens are safe.
- Audit logs include event metadata; apply privileged access, retention
  rules and secure offsite backups. All backup restore testing is external.

## 6. Release/security acceptance

1. Confirm LICENSE/NOTICE, GitHub privacy and authorized user access.
2. Provision secrets, public HTTPS, private Redis, trusted proxy and
   non-superuser PostgreSQL runtime credentials.
3. Apply migrations through head; seed role permission registry and verify
   all document access paths with a restricted runtime DB user.
4. Execute automated tests, PostgreSQL migration round trip and RLS
   integration test on disposable real PostgreSQL 16.
5. Run Nginx -t and test CSP, CORS, headers, caching, cookies,
   auth brute force throttling, session logout and mobile navigation.
6. Benchmark against a *populated staging database*, with concurrent
   signed-in users, p95/p99 request latency, connection and Redis budgets.
7. Perform OWASP API authorization testing, malicious input and XSS
   checks, provider webhook spoof/replay tests, backup/restore rehearsal.
8. Only after external provider/legal/operational signoff tag and deploy a
   production release.

Do not claim zero vulnerabilities or guaranteed instantaneous speed: those
require measured evidence, regular patching and live operational monitoring.
