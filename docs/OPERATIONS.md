# Operational runbook (prelaunch draft)

**Daily:** verify API and DB readiness, Redis and Celery health, disk, backups, unresolved financial transactions, failed provider notifications, and audit anomalies. Do not infer payment success from tenant screenshots.

**Weekly:** restore an encrypted offsite backup into an isolated staging database and verify record counts and invoice/ledger totals. Review dependencies, API and access events, and provider reconciliation.

**Encrypted backup command:** set KATS_BACKUP_DATABASE_URL (a dedicated managed-PostgreSQL backup role), AGE_RECIPIENT and optionally BACKUP_S3_URI, then run bash ops/backup-postgres.sh. Requires PostgreSQL pg_dump/pg_restore, age, and Python 3.12+. It no longer targets a nonexistent Compose db. Never leave the only backup on the VPS. See docs/MANAGED_POSTGRES_RECOVERY.md.

**Destructive staging restore:** set AGE_IDENTITY, RESTORE_DATABASE_URL for a dedicated *_staging or *_restore database and APP_ENV=staging, then execute bash ops/restore-staging.sh --confirm path/to/backup.dump.age. This tool refuses production, primary database names and matching source/target identities. Confirm isolated credentials and backup integrity before executing.

**Payment incident:** suspend settlement if replay/signature failures appear, preserve event evidence and DB snapshot, reconcile against verified payment-provider statements, post authorized financial reversals, and document remediation. An accounting reversal does not send money back to payer.

**EFRIS incident:** do not mark accepted without URA acknowledgment. Queue transient failure retries, preserve payload and response logs with appropriate redaction, and consult the accountant for legally valid corrections.

**Security incident:** contain exposed credentials/sessions, restrict access, preserve logs and evidence, assess tenant-data scope and reporting duties, rotate keys, patch and monitor. Do not publish IDs, PINs, bank credentials or tokens in incident reports.

**Go-live support:** train every role, import verified data, inspect real monthly billing and first rent cycle, and arrange named support escalation. None of this has been performed yet.
