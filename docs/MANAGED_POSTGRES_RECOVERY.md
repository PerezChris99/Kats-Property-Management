# KATS managed PostgreSQL backup and recovery

**Status: source tooling implemented; no offsite backup or witnessed restore has yet been performed.**

These commands replace the previous Docker-Compose `db` backups. The actual
production application runs on external managed PostgreSQL and intentionally
has no `db` container.

## Backup identity and prerequisites

Provision a **dedicated DBA-approved backup role** with access to all relevant
tables, including rows protected by `FORCE ROW LEVEL SECURITY`. The restricted
HTTP runtime account must not be promoted or granted BYPASSRLS merely for
backups. Use provider snapshots/PITR in addition to encrypted logical backups.

Install compatible major-version PostgreSQL `pg_dump` / `pg_restore`, the
`age` encryption CLI and Python 3.12+. For optional private S3-compatible
offsite copies, configure the AWS CLI/endpoint with independently managed
write-only credentials. Install and operate these on a trusted backup runner,
not in the publicly serving API container.

Use environment secrets supplied by your secrets manager:

- `KATS_BACKUP_DATABASE_URL` — separate authorized backup connection URL;
  PostgreSQL TLS `sslmode=verify-full` is mandatory. If unset, the tooling
  uses `DATABASE_URL` but will fail when the runtime role cannot safely dump
  its RLS-protected tables.
- `AGE_RECIPIENT` — approved independent public age encryption recipient.
- `BACKUP_S3_URI` — optional `s3://approved-private-bucket/kats-production/`
  prefix. Omitting it creates only a local encrypted archive and explicitly
  warns **NOT OFFSITE**.
- `KATS_BACKUP_DIR` — optional local encrypted archive directory, default
  `backups/` (gitignored). Keys and decrypted exports must never be in Git.

### Encrypted backup

```bash
export KATS_BACKUP_DATABASE_URL='postgresql+psycopg://BACKUP_USER:SECRET@pg.private:5432/kats?sslmode=verify-full'
export AGE_RECIPIENT='age1YOUR_VERIFIED_RECIPIENT'
export BACKUP_S3_URI='s3://YOUR-PRIVATE-BUCKET/kats-production/'
bash ops/backup-postgres.sh
```

The script uses libpq environment variables to avoid passwords in command
arguments, writes a temporary custom-format PostgreSQL dump, validates the
archive's table inventory, encrypts it with age, writes a SHA-256 sidecar,
and removes the unencrypted temporary dump. Offsite upload uses S3 metadata
SHA-256 verification. Archive integrity alone is **not** restoration evidence.

Require backups to be routinely scheduled with the platform's scheduler or a
`systemd` timer run by an unprivileged dedicated backup operator. Define
retention with the client and counsel, preserve the latest independently
recoverable snapshots, and use provider-managed PITR/WAL for small RPO. Logical
`pg_dump` archives do **not** provide point-in-time recovery.

### Read-only archive verification

```bash
export AGE_IDENTITY='/secure/backup-private-identity.txt'
python3 ops/managed_postgres.py verify --archive backups/kats-YYYYMMDDTHHMMSSZ.dump.age
```

This checks the local SHA-256 sidecar (if present), decrypts to a restricted
temporary directory and validates the PostgreSQL table inventory. The
temporary dump is deleted afterward.

### Isolated staging recovery rehearsal

Never run this against the primary or production database. Provision a
**separate** empty database whose name ends in `_staging` or `_restore`
and use a dedicated authorized staging migrator account. Set `APP_ENV=staging`.
Set `DATABASE_URL` to the primary connection if present so the tool can
also reject source/target identity matches.

```bash
export APP_ENV=staging
export AGE_IDENTITY='/secure/backup-private-identity.txt'
export RESTORE_DATABASE_URL='postgresql+psycopg://RESTORE_ROLE:SECRET@staging-pg.private:5432/kats_restore?sslmode=verify-full'
bash ops/restore-staging.sh --confirm backups/kats-YYYYMMDDTHHMMSSZ.dump.age
```

The restored database must be isolated from public traffic. Verify Alembic
head, seven protected RLS tables, account and tenant row counts, financial
journals, outstanding invoices, audit history, required document-version
metadata, and app startup **before** recording a witnessed restore PASS.
Compare source/target samples with independently signed evidence; do not
publish names or payment details. Retain the proof and recovery duration.

### Recovery runbook and operator signoff

1. Confirm no production traffic points at staging; obtain authorization.
2. Choose a clean, checksum-verified offsite encrypted archive and independent
   age private key stored outside the production host.
3. Obtain managed PostgreSQL staging restore credentials without granting
   them to the HTTP app.
4. Restore and run validation queries in the isolated database.
5. Record RPO/RTO, source archive checksum, time, operator, reviewer,
   application SHA, trial balance and row-count reconciliation.
6. Rehearse application rollback separately; a schema downgrade is not a
   substitute for data recovery. Never silently overwrite posted money.
7. Repeat routinely and after any schema, provider or hosting change.

## Known external gates

- Actual backup role and certificate authority.
- Private S3 retention/versioning, real upload, restore and deletion policies.
- Managed PostgreSQL PITR/WAL retention and provider disaster-recovery SLA.
- Signed operator evidence, financial reconciliation and recovery targets.

Production recovery remains **NOT APPROVED** until these are witnessed.
