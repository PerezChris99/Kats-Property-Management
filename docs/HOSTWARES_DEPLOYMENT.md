# HostWares staging and production plan

**Not deployed or verified.** The Docker Compose stack is development-only, its HTTP ports are localhost-bound, and it has no public HTTPS listener.

## Infrastructure gate

Provision separate staging and production HostWares VPS environments with restricted SSH keys, patched Ubuntu LTS, a firewall with only necessary ports, unique long environment secrets, and dedicated PostgreSQL credentials. Start with 2 vCPU, 4 GB RAM and 80 GB SSD only as a proposed baseline; size using load tests.

Terminate HTTPS at Nginx or Caddy with managed certificate renewal. Require secure session cookies, HTTPS CORS allowlist, HSTS, CSP and signed object-storage file delivery. Do not expose the API or PostgreSQL directly.

## Data and recovery

Set AGE_RECIPIENT to an independently controlled public encryption key and run ops/backup-postgres.sh. Store backups off the VPS with retention, integrity checks and access controls. Weekly, execute ops/restore-staging.sh using AGE_IDENTITY on an isolated staging instance. No production restore command is provided intentionally. Run data count, invoice balance and ledger integrity checks after restoring.

## Release order

1. Pull only a reviewed main commit and keep an immutable image/tag reference.
2. Snapshot and back up current database before a migration.
3. Run backend tests, frontend production build and schema migrations on staging.
4. Check security headers, endpoints, role permissions, privacy and failure states.
5. Run ops/smoke-test.sh against the staging URL.
6. Exercise latency/3G, retry and load tests and verify incidents and alerts.
7. Obtain landlord signoff and tax/payment provider acceptance before production promotion.
8. Confirm production offsite backup, restore evidence and rollback option.
9. Promote and observe the first rent cycle with dedicated on-call support.

## Rollback and incident safety

If a deployment fails, stop writes where needed, preserve a forensic and encrypted backup, and revert to the last compatible image. Schema incompatibility requires a controlled recovery decision. Never delete or rewrite posted monetary records. Coordinate external reconciliation with banks, MTN, Airtel or URA according to the provider and taxpayer rules.

## Monitoring

Configure real uptime, logs, error and resource alerts for API, PostgreSQL, Redis, Celery queues, disk capacity, TLS expiry, failed logins, payment reconciliation and EFRIS submission. All must be tested on real infrastructure. Documentation is not proof that any monitor or alert exists.
